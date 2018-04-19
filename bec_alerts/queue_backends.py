# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import time

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class QueueBackend:
    def receive_events(self):
        raise NotImplementedError()


class SQSQueueBackend(QueueBackend):
    def __init__(
        self,
        queue_name,
        key_id,
        access_key,
        region,
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
            aws_access_key_id=key_id,
            aws_secret_access_key=access_key,
            region_name=region,
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
            VisibilityTimeout=0,
            WaitTimeSeconds=self.wait_time,
        )

        for message in response.get('Messages', []):
            receipt_handle = message['ReceiptHandle']
            yield json.loads(message['Body'])
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
