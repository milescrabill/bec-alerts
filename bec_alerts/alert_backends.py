# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class AlertBackend:
    def send_alert(self, trigger, issues):
        raise NotImplementedError()


class ConsoleAlertBackend(AlertBackend):
    def send_alert(self, trigger, issues):
        print(f'== Alert: {trigger.name}')
        print(f'   Sending to: {",".join(trigger.emails)}')
        print('   Issues:')
        for issue in issues:
            print(f'     {issue.fingerprint}')
        print('')


class EmailAlertBackend(AlertBackend):
    def __init__(
        self,
        from_email,
        key_id,
        access_key,
        region,
        endpoint_url,
        connect_timeout,
        read_timeout,
        verify_email,
    ):
        self.from_email = from_email

        config = Config(connect_timeout=connect_timeout, read_timeout=read_timeout)
        self.ses = boto3.client(
            'ses',
            config=config,
            aws_access_key_id=key_id,
            aws_secret_access_key=access_key,
            region_name=region,
            endpoint_url=endpoint_url,
        )

        if verify_email:
            self.ses.verify_email_identity(EmailAddress=self.from_email)

    def send_alert(self, trigger, issues):
        try:
            self.ses.send_email(
                Destination={'ToAddresses': trigger.emails},
                Message={
                    'Body': {
                        'Text': {
                            'Charset': 'UTF-8',
                            'Data': f'Issues: {",".join(map(lambda i: i.fingerprint, issues))}',
                        },
                    },
                    'Subject': {
                        'Charset': 'UTF-8',
                        'Data': f'Alert: {trigger.name}',
                    },
                },
                Source=self.from_email
            )
        except ClientError as err:
            print(f'Could not send email: {err.response["Error"]["Message"]}')
