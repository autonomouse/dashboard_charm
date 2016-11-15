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


def create_default_user(username, email, uid, apikey):
    provider = "ubuntu"
    hookenv.log('Setting up {} as the default user...'.format(username))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin preseed_default_superuser "
    command += "\"{0}\" \"{1}\" \"{2}\" \"{3}\" \"{4}\"".format(
        username, email, provider, uid, apikey)
    try:
        check_call(shlex.split(command))
    except CalledProcessError:
        err_msg = "Error setting up default weebl user ({})".format(username)
        hookenv.log(err_msg)
        hookenv.status_set('maintenance', err_msg)
        raise Exception(err_msg)


@when('database.master.available', 'nginx.available', 'weebl.ready')
def set_default_credentials(*args, **kwargs):
    if '_apikey' in config:
        hookenv.log('Apikey already set')
        return
    hookenv.log('Setting apikey')
    apikey = utils.get_or_generate_apikey(config.get('apikey'))
    if 'uid' not in config and 'email' in config:
        config['uid'] = config['email'].split('@')[0]
    create_default_user(
        config['username'], config['email'], config['uid'], apikey)
    config['_apikey'] = apikey
    set_state('credentials.available')


@when('oildashboard.connected', 'credentials.available')
def send_default_credentials_to_weebl(oildashboard):
    hookenv.log('Passing weebl username and apikey to oildashboard relation')
    oildashboard.provide_weebl_credentials(
        weebl_username=config['username'],
        weebl_apikey=config['_apikey'])


def migrate_db():
    hookenv.log('Migrating database...')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin migrate --noinput"
    check_call(shlex.split(command))


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

@when('oildashboard.available')
def change_ip_and_debug_mode_in_settings():
    hookenv.log("Changing debug mode and allowed hosts in settings.py")
    utils.edit_weebl_settings(
        config['debug_mode'], hookenv.unit_get('public-address'))
