# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import pytest

from bec_alerts.errors import initialize_error_reporting


@pytest.fixture(scope='session', autouse=True)
def initialization():
    # Re-raise exceptions during test runs
    initialize_error_reporting(reraise=True)
