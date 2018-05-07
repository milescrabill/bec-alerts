# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.template.loader import render_to_string

from bec_alerts.models import User, UserIssue


class Trigger:
    name = 'Error'
    emails = []
    template = 'basic_alert.txt'
    subject_template = '[Firefox Browser Errors] {trigger.name}: {issue.message}'

    def __init__(self, alert_backend, dry_run, now):
        self.alert_backend = alert_backend
        self.dry_run = dry_run
        self.now = now

    def get_users(self):
        users = []
        for email in self.emails:
            user, created = User.objects.get_or_create(email=email)
            users.append(user)
        return users

    def alert_user(self, user, issue):
        alert_body = render_to_string(self.template, {
            'user': user,
            'issue': issue,
            'trigger': self,
        })
        subject = self.subject_template.format(
            issue=issue,
            user=user,
            trigger=self,
        )
        self.alert_backend.send_alert(to=user.email, subject=subject, body=alert_body)

        if not self.dry_run:
            user_issue, created = UserIssue.objects.get_or_create(user=user, issue=issue)
            user_issue.last_notified = self.now
            user_issue.save()

    def evaluate(self, issue):
        raise NotImplementedError()


class AlwaysNotifyTrigger(Trigger):
    emails = ['test@example.com']
    name = 'Error'

    def evaluate(self, issue):
        for user in self.get_users():
            self.alert_user(user, issue)


class NewNotifyTrigger(Trigger):
    emails = ['test@example.com']
    name = 'New Error'

    def evaluate(self, issue):
        for user in self.get_users():
            if not user.has_been_notified_about(issue):
                self.alert_user(user, issue)


def get_trigger_classes():
    return Trigger.__subclasses__()
