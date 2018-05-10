import logging
import traceback

import raven


reporter = None


def initialize_error_reporting(sentry_dsn=None):
    global reporter
    if sentry_dsn:
        reporter = SentryReporter(sentry_dsn)
    else:
        reporter = LoggingReporter()


def captureException(message=None):
    global reporter
    if reporter is None:
        raise RuntimeError('Cannot capture exception: initialize_error_reporting was not called')
    reporter.captureException(message)


class SentryReporter:
    def __init__(self, sentry_dsn):
        self.client = raven.Client(sentry_dsn)

    def captureException(self, message):
        self.client.captureException(extra={'message': message})


class LoggingReporter:
    def captureException(self, message):
        # Create logger here since logging may not be configured at import time.
        logger = logging.getLogger('bec-alerts.errors')
        if message:
            logger.error(message)
        logger.error(traceback.format_exc())
