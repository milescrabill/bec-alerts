# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from pathlib import Path

BASE_DIR = Path(__file__).joinpath('..', '..').resolve()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR.joinpath('db.sqlite3')),
    }
}

USE_TZ = True

INSTALLED_APPS = (
    'bec_alerts',
)

SECRET_KEY = '!!!SECRET!!!'
