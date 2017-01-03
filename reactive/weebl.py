#!/usr/bin/env python3

import os
import shlex
from charmhelpers.core import hookenv
from charms.reactive import when, set_state
from charms.layer.weebl import utils
from subprocess import check_call, CalledProcessError

config = hookenv.config()


@when('database.connected')
def request_db(pgsql):
    if hookenv.in_relation_hook():
        hookenv.log('Setting db relation options')
        pgsql.set_database('bugs_database')
        pgsql.set_extensions('tablefunc')
        pgsql.set_roles('weebl')


@when('database.master.available', 'nginx.available', 'weebl.ready')
def set_default_credentials(*args, **kwargs):
    if '_apikey' in config:
        hookenv.log('Apikey already set')
        return
    hookenv.log('Setting apikey')
    apikey = utils.get_or_generate_apikey(config.get('apikey'))
    if 'uid' not in config and 'email' in config:
        config['uid'] = config['email'].split('@')[0]
    utils.create_default_user(
        config['username'], config['email'], config['uid'], apikey)
    config['_apikey'] = apikey
    set_state('credentials.available')


@when('oildashboard.connected', 'credentials.available')
def send_default_credentials_to_weebl(oildashboard):
    hookenv.log('Passing weebl username and apikey to oildashboard relation')
    oildashboard.provide_weebl_credentials(
        weebl_username=config['username'],
        weebl_apikey=config['_apikey'])


@when('database.master.available', 'nginx.available', 'config.changed')
def install_weebl(*args, **kwargs):
    utils.install_weebl(config)


@when('database.master.available', 'nginx.available')
def setup_database(pgsql):
    if hookenv.in_relation_hook():
        hookenv.log('Configuring weebl db!')
        hookenv.status_set('maintenance', 'weebl is connecting to pgsql!')
        utils.render_config(pgsql)
        utils.install_weebl(config)
