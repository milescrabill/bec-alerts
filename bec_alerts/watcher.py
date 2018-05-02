# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import click
import time
import traceback
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from bec_alerts.alert_backends import ConsoleAlertBackend, EmailAlertBackend
from bec_alerts.models import Issue, TriggerRun, User
from bec_alerts.triggers import triggers
from bec_alerts.utils import latest_nightly_appbuildid


def process_triggers(alert_backend, now):
    last_finished_run = TriggerRun.objects.filter(finished=True).order_by('-ran_at').first()
    if last_finished_run:
        issues = Issue.objects.filter(last_seen__gte=last_finished_run.ran_at)
    else:
        issues = Issue.objects.all()

    # Clear caches since we're starting a new run
    latest_nightly_appbuildid.cache_clear()

    # Evaluate triggers
    alerts_to_send = []
    for trigger in triggers:
        for email in trigger.emails:
            user, created = User.objects.get_or_create(email=email)
            for issue in issues:
                if trigger(user, issue):
                        alerts_to_send.append((trigger, user, issue))

    # Send notifications
    for trigger, user, issue in alerts_to_send:
        # Don't abort just because we failed to send a single notification
        try:
            alert_backend.handle_alert(now, trigger, user, issue)
        except Exception as err:
            print(
                f'Error sending notification for trigger {trigger.name} (issue '
                f'{issue.fingerprint}) to user {user.email}'
            )
            traceback.print_exc()


@transaction.atomic
def run_job(
    dry_run,
    alert_backend,
    from_email,
    endpoint_url,
    connect_timeout,
    read_timeout,
    verify_email,
):
    now = timezone.now()

    if dry_run:
        process_triggers(alert_backend, now)
    else:
        current_run = TriggerRun(ran_at=now, finished=False)
        current_run.save()

        process_triggers(alert_backend, now)

        current_run.finished = True
        current_run.save()

        # Remove run logs older than 7 days
        TriggerRun.objects.filter(ran_at__lte=now - timedelta(days=7)).delete()


@click.command()
@click.option('--once', is_flag=True, default=False)
@click.option('--dry-run', is_flag=True, default=False)
@click.option('--console-alerts', is_flag=True, default=False)
@click.option('--verify-email', is_flag=True, default=False, envvar='SES_VERIFY_EMAIL')
@click.option('--sleep-delay', default=300, envvar='WATCHER_SLEEP_DELAY')
@click.option('--from-email', default='notifications@sentry.prod.mozaws.net', envvar='SES_FROM_EMAIL')
@click.option('--endpoint-url', envvar='SES_ENDPOINT_URL')
@click.option('--connect-timeout', default=30, envvar='AWS_CONNECT_TIMEOUT')
@click.option('--read-timeout', default=30, envvar='AWS_READ_TIMEOUT')
def main(
    once,
    dry_run,
    console_alerts,
    sleep_delay,
    from_email,
    endpoint_url,
    connect_timeout,
    read_timeout,
    verify_email,
):
    if console_alerts:
        alert_backend = ConsoleAlertBackend(dry_run=dry_run)
    else:
        alert_backend = EmailAlertBackend(
            dry_run=dry_run,
            from_email=from_email,
            endpoint_url=endpoint_url,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            verify_email=verify_email,
        )

    while True:
        try:
            run_job(
                dry_run=dry_run,
                alert_backend=alert_backend,
                from_email=from_email,
                endpoint_url=endpoint_url,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                verify_email=verify_email,
            )
        except Exception as err:
            print(f'Error running triggers:')
            traceback.print_exc()

        if once:
            break
        time.sleep(sleep_delay)
