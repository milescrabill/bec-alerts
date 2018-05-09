# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import time
from datetime import timedelta

import click
import datadog
from django.db import transaction
from django.utils import timezone

from bec_alerts.alert_backends import ConsoleAlertBackend, EmailAlertBackend
from bec_alerts.errors import captureException, initialize_error_reporting
from bec_alerts.models import Issue, TriggerRun
from bec_alerts.triggers import get_trigger_classes
from bec_alerts.utils import latest_nightly_appbuildid


def evaluate_triggers(alert_backend, dry_run, now):
    last_finished_run = TriggerRun.objects.filter(finished=True).order_by('-ran_at').first()
    if last_finished_run:
        issues = Issue.objects.filter(last_seen__gte=last_finished_run.ran_at)
    else:
        issues = Issue.objects.all()

    # Clear caches since we're starting a new run
    latest_nightly_appbuildid.cache_clear()

    # Evaluate triggers
    for trigger_class in get_trigger_classes():
        trigger = trigger_class(alert_backend, dry_run, now)
        for issue in issues:
            trigger.evaluate(issue)


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
        evaluate_triggers(alert_backend, dry_run, now)
    else:
        current_run = TriggerRun(ran_at=now, finished=False)
        current_run.save()

        evaluate_triggers(alert_backend, dry_run, now)

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
@click.option('--datadog-api-key', envvar='DATADOG_API_KEY')
@click.option('--datadog-counter-name', envvar='DATADOG_COUNTER_NAME', default='bec-alerts.watcher.health')
@click.option('--sentry-dsn', envvar='SENTRY_DSN')
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
    datadog_api_key,
    datadog_counter_name,
    sentry_dsn,
):
    initialize_error_reporting(sentry_dsn)

    try:
        if datadog_api_key:
            datadog.initialize(api_key=datadog_api_key)

        if console_alerts:
            alert_backend = ConsoleAlertBackend()
        else:
            alert_backend = EmailAlertBackend(
                from_email=from_email,
                endpoint_url=endpoint_url,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                verify_email=verify_email,
            )
    except Exception:
        # Just make sure Sentry knows that we failed on startup
        captureException()
        raise

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
            captureException(f'Error running triggers')
        finally:
            if datadog_api_key:
                datadog.statsd.increment(datadog_counter_name)

        if once:
            break
        time.sleep(sleep_delay)
