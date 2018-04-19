# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.db import models


class User(models.Model):
    email = models.EmailField(unique=True)


class Issue(models.Model):
    fingerprint = models.CharField(max_length=255, unique=True)
    last_seen = models.DateTimeField(null=True, default=None)


class TriggerRun(models.Model):
    ran_at = models.DateTimeField()
    finished = models.BooleanField(default=False)
