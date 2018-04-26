# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import click
import os
import time
import traceback
from datetime import datetime
from multiprocessing import Process

from django.utils import timezone

from bec_alerts.models import Issue, IssueBucket
from bec_alerts.queue_backends import SQSQueueBackend


def process_event(event):
    # Fingerprints are actually an array of values, but we only use the
    # default fingerprint algorithm, which uses a single value.
    fingerprint = event['fingerprints'][0]
    naive_datetime_received = datetime.strptime(event['dateReceived'], '%Y-%m-%dT%H:%M:%S.%fZ')
    datetime_received = timezone.make_aware(naive_datetime_received, timezone=timezone.utc)

    # Create issue, or update the last_seen date for it
    issue, created = Issue.objects.get_or_create(fingerprint=fingerprint, defaults={
        'last_seen': datetime_received,
    })
    if not created and issue.last_seen < datetime_received:
        issue.last_seen = datetime_received
        issue.save()

    # Increment the event count bucket
    bucket, created = IssueBucket.objects.get_or_create(
        issue=issue,
        date=datetime_received.date(),
    )
    bucket.count_event(event['eventID'])


def listen(
    sleep_delay,
    queue_name,
    endpoint_url,
    connect_timeout,
    read_timeout,
):
    queue_backend = SQSQueueBackend(
        queue_name=queue_name,
        endpoint_url=endpoint_url,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )

    print('Waiting for an event...')
    while True:
        try:
            for event in queue_backend.receive_events():
                print(f'Received event: {event["eventID"]}')
                try:
                    process_event(event)
                except Exception as err:
                    print(f'Error processing event: {event["eventID"]}')
                    traceback.print_exc()
        except Exception as err:
            print(f'Error receiving message: {err}')
            time.sleep(sleep_delay)


@click.command()
@click.option('--sleep-delay', default=20, envvar='PROCESSOR_SLEEP_DELAY')
@click.option('--queue-name', default='sentry_errors', envvar='SQS_QUEUE_NAME')
@click.option('--endpoint-url', envvar='SQS_ENDPOINT_URL')
@click.option('--connect-timeout', default=30, envvar='AWS_CONNECT_TIMEOUT')
@click.option('--read-timeout', default=30, envvar='AWS_READ_TIMEOUT')
@click.option('--process_count', default=os.cpu_count(), envvar='PROCESSOR_PROCESS_COUNT')
def main(
    sleep_delay,
    queue_name,
    endpoint_url,
    connect_timeout,
    read_timeout,
    process_count,
):
    print('Starting processor workers')
    processes = []
    for k in range(process_count):
        process = Process(target=listen, kwargs={
            'sleep_delay': sleep_delay,
            'queue_name': queue_name,
            'endpoint_url': endpoint_url,
            'connect_timeout': connect_timeout,
            'read_timeout': read_timeout,
        })
        process.start()
        processes.append(process)
