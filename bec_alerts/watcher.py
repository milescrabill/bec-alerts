# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import click
import time
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from bec_alerts.alert_backends import ConsoleAlertBackend, EmailAlertBackend
from bec_alerts.models import Issue, TriggerRun
from bec_alerts.triggers import triggers


@transaction.atomic
def process_triggers(alert_backend):
    last_finished_run = TriggerRun.objects.filter(finished=True).order_by('-ran_at').first()
    if last_finished_run:
        issues = Issue.objects.filter(last_seen__gte=last_finished_run.ran_at)
    else:
        issues = Issue.objects.all()

    # Evaluate triggers
    triggered_issues = {}
    for trigger in triggers:
        triggered_issues[trigger] = []
        for issue in issues:
            if trigger(None, issue):
                triggered_issues[trigger].append(issue)

    # Send notifications
    for trigger, issues in triggered_issues.items():
        if issues:
            alert_backend.send_alert(trigger, issues)


def run_job(
    dry_run,
    from_email,
    key_id,
    access_key,
    region,
    endpoint_url,
    connect_timeout,
    read_timeout,
    verify_email,
):
    if dry_run:
        alert_backend = ConsoleAlertBackend()
        process_triggers(alert_backend)
    else:
        current_run = TriggerRun(ran_at=timezone.now(), finished=False)
        current_run.save()

        alert_backend = EmailAlertBackend(
            from_email=from_email,
            key_id=key_id,
            access_key=access_key,
            region=region,
            endpoint_url=endpoint_url,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            verify_email=verify_email,
        )
        process_triggers(alert_backend)

        current_run.finished = True
        current_run.save()

        # Remove run logs older than 7 days
        TriggerRun.objects.filter(ran_at__lte=current_run.ran_at - timedelta(days=7)).delete()


def validate_optional_for_dry_run(ctx, param, value):
    if not value and not ctx.params['dry_run']:
        raise click.BadParameter('Option is required unless --dry-run option is passed')
    return value


def wet_run_option(*args, **kwargs):
    kwargs.setdefault('callback', validate_optional_for_dry_run)
    return click.option(*args, **kwargs)


@click.command()
@click.option('--once', is_flag=True, default=False)
@click.option('--dry-run', is_flag=True, default=False, is_eager=True)
@click.option('--verify-email', is_flag=True, default=False, envvar='SES_VERIFY_EMAIL')
@click.option('--sleep-delay', default=300, envvar='WATCHER_SLEEP_DELAY')
@click.option('--from-email', default='notifications@sentry.prod.mozaws.net', envvar='SES_FROM_EMAIL')
@click.option('--endpoint-url', envvar='SES_ENDPOINT_URL')
@click.option('--connect-timeout', default=30, envvar='AWS_CONNECT_TIMEOUT')
@click.option('--read-timeout', default=30, envvar='AWS_READ_TIMEOUT')
@wet_run_option('--key-id', prompt=True, envvar='AWS_ACCESS_KEY_ID')
@wet_run_option('--access-key', prompt=True, hide_input=True, envvar='AWS_SECRET_ACCESS_KEY')
@wet_run_option('--region', prompt=True, envvar='AWS_DEFAULT_REGION')
def main(
    once,
    dry_run,
    sleep_delay,
    from_email,
    key_id,
    access_key,
    region,
    endpoint_url,
    connect_timeout,
    read_timeout,
    verify_email,
):
    while True:
        try:
            run_job(
                dry_run=dry_run,
                from_email=from_email,
                key_id=key_id,
                access_key=access_key,
                region=region,
                endpoint_url=endpoint_url,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                verify_email=verify_email,
            )
        except Exception as err:
            print(f'Error running triggers: {err}')

        if once:
            break
        time.sleep(sleep_delay)
