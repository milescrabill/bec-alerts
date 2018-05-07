#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import click
import os
import sys
from pathlib import Path

import django
from dotenv import load_dotenv
from raven import Client

dotenv_path = Path(__file__).joinpath('..', '..', '.env').resolve()
load_dotenv(dotenv_path=dotenv_path)

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bec_alerts.settings")
django.setup()

from django.core.management import execute_from_command_line  # NOQA
from bec_alerts.processor import main as processor_main  # NOQA
from bec_alerts.watcher import main as watcher_main  # NOQA


@click.group()
def cli():
    pass


@cli.command()
@click.argument('manage_args', nargs=-1)
def manage(manage_args):
    execute_from_command_line(['', *manage_args])


@cli.command()
@click.option('--dsn', envvar='SENTRY_DSN')
@click.option('--message', default='Simulated error')
@click.option('--fingerprint', default='{{ default }}')
@click.option('--traceback/--no-traceback', default=True)
def simulate_error(dsn, message, fingerprint, traceback):
    if not dsn:
        raise RuntimeError(
            'A DSN must be provided by either the --dsn argument or SENTRY_DSN environment '
            'variable.'
        )

    client = Client(dsn)
    try:
        raise Exception(message)
    except Exception:
        err_type, err_value, err_traceback = sys.exc_info()
        exc_info = (err_type, err_value, err_traceback if traceback else None)
        client.captureException(exc_info=exc_info, fingerprint=[fingerprint])
    print('Error sent')


cli.add_command(processor_main, name='processor')
cli.add_command(watcher_main, name='watcher')


if __name__ == "__main__":
    cli()
