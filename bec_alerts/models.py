# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.db import connection, models
from django.utils import timezone


class User(models.Model):
    email = models.EmailField(unique=True)


class Issue(models.Model):
    fingerprint = models.CharField(max_length=255, unique=True)
    last_seen = models.DateTimeField(null=True, default=None)


class TriggerRun(models.Model):
    ran_at = models.DateTimeField()
    finished = models.BooleanField(default=False)


class HyperLogLogField(models.Field):
    def __init__(self, *args, **kwargs):
        kwargs['default'] = self.default_value
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['default']
        return name, path, args, kwargs

    def default_value(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT hll_empty()')
            return cursor.fetchone()[0]

    def db_type(self, connection):
        return 'hll'


class IssueBucketManager(models.Manager):
    def event_count(self, issue=None, start_date=None, end_date=None):
        with connection.cursor() as cursor:
            query = '''
                SELECT
                    hll_cardinality(hll_union_agg(count_set))
                FROM bec_alerts_issuebucket
            '''

            where_clauses = []
            params = {}

            if issue:
                where_clauses.append('issue_id = %(issue_id)s')
                params['issue_id'] = issue.id

            if start_date:
                where_clauses.append('date >= %(start_date)s')
                params['start_date'] = start_date

            if end_date:
                where_clauses.append('date <= %(end_date)s')
                params['end_date'] = end_date

            if where_clauses:
                query += f'WHERE {" AND ".join(where_clauses)}'

            cursor.execute(query, params)
            return cursor.fetchone()[0]


class IssueBucket(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    count_set = HyperLogLogField()

    objects = IssueBucketManager()

    class Meta:
        unique_together = ['issue', 'date']

    def count_event(self, event_id):
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE bec_alerts_issuebucket
                    SET count_set = hll_add(count_set, hll_hash_text(%s))
                WHERE id = %s
                ''',
                (event_id, self.id),
            )
