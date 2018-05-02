# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from bec_alerts.models import UserIssue


class AlertBackend:
    def __init__(self, dry_run):
        self.dry_run = dry_run

    def handle_alert(self, now, trigger, user, issue):
        self.send_alert(trigger, user, issue)
        if not self.dry_run:
            user_issue, created = UserIssue.objects.get_or_create(user=user, issue=issue)
            user_issue.last_notified = now
            user_issue.save()

    def send_alert(self, trigger, user, issue):
        raise NotImplementedError()


class ConsoleAlertBackend(AlertBackend):
    def send_alert(self, trigger, user, issue):
        print(f'== Alert: {trigger.name}')
        print(f'   Sending to: {user.email}')
        print(f'   Issue: {issue.fingerprint}')
        print('')


class EmailAlertBackend(AlertBackend):
    def __init__(
        self,
        dry_run,
        now,
        from_email,
        endpoint_url,
        connect_timeout,
        read_timeout,
        verify_email,
    ):
        super().__init__(dry_run=dry_run, now=now)
        self.from_email = from_email

        config = Config(connect_timeout=connect_timeout, read_timeout=read_timeout)
        self.ses = boto3.client(
            'ses',
            config=config,
            endpoint_url=endpoint_url,
        )

        if verify_email:
            self.ses.verify_email_identity(EmailAddress=self.from_email)

    def send_alert(self, trigger, user, issue):
        try:
            self.ses.send_email(
                Destination={'ToAddresses': [user.email]},
                Message={
                    'Body': {
                        'Text': {
                            'Charset': 'UTF-8',
                            'Data': f'Issue: {issue.fingerprint}',
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
