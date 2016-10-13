#!/usr/bin/env python3
import os
import shlex
import yaml
from charms.reactive import (
    when,
    set_state,
    )
from charmhelpers.core import hookenv
from charmhelpers.core.templating import render
from subprocess import check_call, CalledProcessError
from charms.layer.weebl import utils
from charms.layer.weebl.constants import JSLIBS_DIR, WEEBL_PKG

config = hookenv.config()


@when('database.connected')
def request_db(pgsql):
    if hookenv.in_relation_hook():
        hookenv.log('Setting db relation options')
        pgsql.set_database('bugs_database')
        pgsql.set_extensions('tablefunc')
        pgsql.set_roles('weebl')


def setup_weebl_gunicorn_service():
    render(
        source="weebl-gunicorn.service",
        target="/lib/systemd/system/weebl-gunicorn.service",
        context={'extra_options': config['extra_options']})
    utils.cmd_service('enable', 'weebl-gunicorn', hookenv)


def setup_weebl_site(weebl_name):
    hookenv.log('Setting up weebl site...')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin set_up_site \"{}\"".format(weebl_name)
    try:
        check_call(shlex.split(command))
    except CalledProcessError:
        err_msg = "Error setting up weebl"
        hookenv.log(err_msg)


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


@when('oildashboard.connected', 'database.master.available', 'nginx.available')
def set_default_credentials_and_send_to_weebl(oildashboard, *args, **kwargs):
    if '_apikey' in config and (config['apikey'] == config['_apikey']):
        hookenv.log('Apikey already set')
        return
    hookenv.log('Setting apikey')
    apikey = utils.get_or_generate_apikey(config.get('apikey'), hookenv)
    create_default_user(
        config['username'], config['email'], config['uid'], apikey)
    oildashboard.provide_weebl_credentials(
        weebl_username=config['username'],
        weebl_apikey=apikey)
    config['_apikey'] = apikey


def load_fixtures():
    hookenv.log('Loading fixtures...')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin loaddata initial_settings.yaml"
    check_call(shlex.split(command))


def migrate_db():
    hookenv.log('Migrating database...')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin migrate --noinput"
    check_call(shlex.split(command))


@when('database.master.available', 'nginx.available', 'config.changed')
def install_weebl(*args, **kwargs):
    hookenv.status_set('maintenance', 'Installing Weebl...')
    weebl_ready = False
    if utils.install_deb(WEEBL_PKG, config, hookenv):
        weebl_ready = utils.install_npm_deps(hookenv)
    else:
        return False
    setup_weebl_gunicorn_service()
    utils.cmd_service('start', 'weebl-gunicorn', hookenv)
    utils.cmd_service('restart', 'nginx', hookenv)
    setup_weebl_site(config['username'])
    utils.fix_bundle_dir_permissions()
    if not weebl_ready:
        raise Exception('Weebl installation failed')
    load_fixtures()
    return weebl_ready


def render_config(pgsql):
    db_settings = {
        'host':  pgsql.master['host'],
        'port': pgsql.master['port'],
        'database': pgsql.master['dbname'],
        'user': pgsql.master['user'],
        'password': pgsql.master['password'],
    }
    db_config = {
        'database': db_settings,
        'static_root': JSLIBS_DIR,
    }
    utils.mkdir_p('/etc/weebl/')
    with open('/etc/weebl/weebl.yaml', 'w') as weebl_db:
        weebl_db.write(yaml.dump(db_config))


@when('database.master.available', 'nginx.available')
def setup_database(pgsql):
    if hookenv.in_relation_hook():
        hookenv.log('Configuring weebl db!')
        hookenv.status_set('maintenance', 'weebl is connecting to pgsql!')
        render_config(pgsql)
        if install_weebl():
            hookenv.status_set('active', 'Ready')
        else:
            hookenv.status_set('maintenance', 'Weebl installation failed')
