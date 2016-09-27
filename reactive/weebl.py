#!/usr/bin/env python3
import os
import errno
import yaml
import shlex

from string import hexdigits
from random import choice

from subprocess import check_call, CalledProcessError

from charmhelpers.core import hookenv
from charmhelpers.core.templating import render
from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
    )

from charms.reactive import (
    when,
    set_state,
    )


JSLIBS_DIR = '/var/lib/weebl/static'


config = hookenv.config()
weebl_pkg = 'python3-weebl'


def mkdir_p(directory_name):
    try:
        os.makedirs(directory_name)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(directory_name):
            raise exc


def cmd_service(cmd, service):
    command = "systemctl {} {}".format(cmd, service)
    hookenv.log(command)
    check_call(shlex.split(command))


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
    cmd_service('enable', 'weebl-gunicorn')


def install_weebl_deb():
    hookenv.log('Installing/upgrading weebl!')
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    try:
        add_source(ppa, ppa_key)
    except Exception:
        hookenv.log("Error adding source PPA: {}".format(ppa))
    try:
        apt_update()
        apt_install([weebl_pkg])
    except Exception as e:
        hookenv.log(str(e))
        return False
    return True


def setup_weebl_site(weebl_name):
    hookenv.log('Setting up weebl site...')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin set_up_site \"{}\"".format(weebl_name)
    try:
        check_call(shlex.split(command))
    except CalledProcessError:
        err_msg = "Error setting up weebl"
        hookenv.log(err_msg)


def get_or_generate_apikey():
    if config['apikey'] not in [None, ""]:
        return config['apikey']
    else:
        hookenv.log("No apikey provided - generating random apikey.")
        return ''.join([choice(hexdigits[:16]) for _ in range(40)])


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
    apikey = get_or_generate_apikey()
    create_default_user(
        config['username'], config['email'], config['uid'], apikey)
    oildashboard.provide_weebl_credentials(
        weebl_username=config['username'],
        weebl_apikey=apikey)


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


def install_npm_deps():
    weebl_ready = True
    hookenv.log('Installing npm packages...')
    mkdir_p(JSLIBS_DIR)
    npm_pkgs = [
        "d3@3.5.17",
        "nvd3@1.8.3",
        "angular-nvd3@1.0.7"]
    for npm_pkg in npm_pkgs:
        command = "npm install --prefix {} {}".format(
            JSLIBS_DIR, npm_pkg)
        try:
            check_call(shlex.split(command))
        except CalledProcessError:
            err_msg = "Failed to install {} via npm".format(npm_pkg)
            hookenv.log(err_msg)
            weebl_ready = False
    return weebl_ready


@when('database.master.available', 'nginx.available', 'config.changed')
def install_weebl(*args, **kwargs):
    weebl_ready = False
    if install_weebl_deb():
        weebl_ready = install_npm_deps()
    setup_weebl_gunicorn_service()
    cmd_service('start', 'weebl-gunicorn')
    cmd_service('restart', 'nginx')
    load_fixtures()
    setup_weebl_site(config['weebl_name'])
    fix_bundle_dir_permissions()
    if not weebl_ready:
        hookenv.status_set('maintenance', 'Weebl installation failed')
        raise Exception('Weebl installation failed')


def fix_bundle_dir_permissions():
    chown_cmd = "chown www-data {}/img/bundles/".format(JSLIBS_DIR)
    check_call(shlex.split(chown_cmd))


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
    mkdir_p('/etc/weebl/')
    with open('/etc/weebl/weebl.yaml', 'w') as weebl_db:
        weebl_db.write(yaml.dump(db_config))


@when('database.master.available', 'nginx.available')
def setup_database(pgsql):
    if hookenv.in_relation_hook():
        hookenv.log('Configuring weebl db!')
        hookenv.status_set('maintenance', 'weebl is connecting to pgsql!')
        render_config(pgsql)
        install_weebl()
        hookenv.status_set('active', 'Ready')
