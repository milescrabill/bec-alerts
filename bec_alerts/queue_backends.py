# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import time

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class QueueBackend:
    """
    Base class for backends that listen for incoming Sentry events.
    """
    def receive_events(self):
        """
        :returns:
            An iterator filled with Sentry events. It may potentially
            be empty if no new events are available, and may block while
            it polls for new events.
        """
        raise NotImplementedError()


class SQSQueueBackend(QueueBackend):
    """Listen for incoming events from an Amazon SQS queue."""
    def __init__(
        self,
        queue_name,
        endpoint_url,
        connect_timeout,
        read_timeout,
    ):
        # If wait time and read_timeout are the same, the connection times out
        # before AWS (or at least localstack) can send us an empty response. A 2
        # second buffer helps avoid this.
        self.wait_time = min(20, read_timeout - 2)

        config = Config(connect_timeout=connect_timeout, read_timeout=read_timeout)
        self.sqs = boto3.client(
            'sqs',
            config=config,
            endpoint_url=endpoint_url,
        )

        while True:
            try:
                response = self.sqs.create_queue(QueueName=queue_name)
                break
            except ClientError as err:
                print(f'Error creating queue: {err}')
                time.sleep(5)

        self.queue_url = response['QueueUrl']

    def receive_events(self):
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=10,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=30,
            WaitTimeSeconds=self.wait_time,
        )

        for message in response.get('Messages', []):
            receipt_handle = message['ReceiptHandle']
            yield json.loads(message['Body'])
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
