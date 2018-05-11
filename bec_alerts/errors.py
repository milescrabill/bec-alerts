# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
import sys
import traceback

import raven


reporter = None


def initialize_error_reporting(sentry_dsn=None, reraise=False):
    """
    Choose which reporting backend to use. Must be called before
    captureException.
    """
    global reporter
    if sentry_dsn:
        reporter = SentryReporter(sentry_dsn)
    else:
        reporter = LoggingReporter(reraise)


def capture_exception(message=None):
    """Call capture_exception on the configured reporting backend."""
    global reporter
    if reporter is None:
        raise RuntimeError('Cannot capture exception: initialize_error_reporting was not called')
    reporter.capture_exception(message)


class SentryReporter:
    """Reports errors to a Sentry instance."""
    def __init__(self, sentry_dsn):
        self.client = raven.Client(sentry_dsn)

    def capture_exception(self, message):
        self.client.captureException(extra={'message': message})


class LoggingReporter:
    """Logs errors to the bec-alerts.errors logger."""
    def __init__(self, reraise):
        self.reraise = reraise

    def capture_exception(self, message):
        # Create logger here since logging may not be configured at import time.
        logger = logging.getLogger('bec-alerts.errors')
        if message:
            logger.error(message)

        if self.reraise:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise exc_value
        else:
            logger.error(traceback.format_exc())
