# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from random import randint
from uuid import uuid4

import pytest
from django.utils import timezone

from bec_alerts.processor import listen
from bec_alerts.queue_backends import StaticQueueBackend


def stack_frame(**kwargs):
    return {
        'function': kwargs.get('function', 'funcname'),
        'module': kwargs.get('module', 'resource://fake.jsm'),
        'lineMo': kwargs.get('lineNo', 17),
        'colNo': kwargs.get('colNo', 56),
    }


def sentry_event(date=None, module='resource://fake.jsm', stack_frames=None, **kwargs):
    """
    Create a mock Sentry event. This only covers attributes we use.
    """
    event = {
        'eventID': kwargs.get('eventID', str(uuid4())),
        'message': kwargs.get('message', 'Error: fake error'),
        'dateReceived': (date or timezone.now()).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'groupID': kwargs.get('groupID', randint(1, 999999)),
        'fingerprints': kwargs.get('fingerprints', [str(uuid4())]),
        'entries': kwargs.get('entries', [
            {
                'type': 'exception',
                'data': {
                    'values': [
                        {
                            'module': module,
                            'stacktrace': {
                                'frames': stack_frames or [
                                    stack_frame(),
                                ],
                            },
                        },
                    ],
                },
            },
        ]),
    }

    return event


@pytest.mark.django_db
def test_listen_works():
    queue_backend = StaticQueueBackend([sentry_event()])
    listen(
        sleep_delay=0,
        queue_backend=queue_backend,
        worker_message_count=1,
    )
