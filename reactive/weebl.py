#!/usr/bin/env python3

import errno
from lib import common

from charmhelpers.core import hookenv
from charmhelpers.core.templating import render

from charms.reactive import (
    hook,
    when,
    only_once,
    set_state,
    remove_state,
    )


@hook('db-relation-joined')
def request_db(pgsql):
    common.request_db(pgsql)


@when('database.database.available', 'nginx.available')
def setup_database(pgsql):
    common.setup_database(pgsql)
