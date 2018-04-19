# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import click
import time

from django.utils import timezone

from bec_alerts.models import Issue
from bec_alerts.queue_backends import SQSQueueBackend


def process_event(event):
    # Fingerprints are actually an array of values, but we only use the
    # default fingerprint algorithm, which uses a single value.
    fingerprint = event['fingerprints'][0]
    issue, created = Issue.objects.get_or_create(fingerprint=fingerprint, defaults={
        'last_seen': timezone.now(),
    })

    if not created:
        issue.last_seen = timezone.now()
        issue.save()


@click.command()
@click.option('--sleep-delay', default=20, envvar='PROCESSOR_SLEEP_DELAY')
@click.option('--queue-name', default='sentry_errors', envvar='SQS_QUEUE_NAME')
@click.option('--key-id', prompt=True, envvar='AWS_ACCESS_KEY_ID')
@click.option('--access-key', prompt=True, hide_input=True, envvar='AWS_SECRET_ACCESS_KEY')
@click.option('--region', prompt=True, envvar='AWS_DEFAULT_REGION')
@click.option('--endpoint-url', envvar='SQS_ENDPOINT_URL')
@click.option('--connect-timeout', default=30, envvar='AWS_CONNECT_TIMEOUT')
@click.option('--read-timeout', default=30, envvar='AWS_READ_TIMEOUT')
def main(
    sleep_delay,
    queue_name,
    key_id,
    access_key,
    region,
    endpoint_url,
    connect_timeout,
    read_timeout,
):
    print('Starting processor')
    queue_backend = SQSQueueBackend(
        queue_name=queue_name,
        key_id=key_id,
        access_key=access_key,
        region=region,
        endpoint_url=endpoint_url,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )

    print('Waiting for an event...')
    while True:
        try:
            for event in queue_backend.receive_events():
                print(f'Received event: {event["eventID"]}')
                process_event(event)
        except Exception as err:
            print(f'Error receiving message: {err}')
            time.sleep(sleep_delay)
