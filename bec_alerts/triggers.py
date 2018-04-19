# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
triggers = []


def trigger(trigger_name, *emails):
    def wrapper(trigger_func):
        if trigger_name in triggers:
            raise RuntimeError(f'A trigger named "{trigger_name}" has already been defined.')

        trigger_func.name = trigger_name
        trigger_func.emails = emails
        triggers.append(trigger_func)
        return trigger_func
    return wrapper


@trigger('Test notification', 'test@example.com')
def should_notify_test(user, issue):
    return True
