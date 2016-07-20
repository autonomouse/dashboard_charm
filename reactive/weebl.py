#!/usr/bin/env python3
import os
import errno
import yaml
import shlex

from uuid import uuid4
from random import randint
from subprocess import check_call, CalledProcessError

from charmhelpers.core import hookenv
from charmhelpers.core.templating import render
from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
    )

from charms.reactive import (
    hook,
    when,
    only_once,
    set_state,
    remove_state,
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
    hookenv.log('Setting db relation options')
    pgsql.change_database_name('bugs_database')
    pgsql.set_remote('extensions', 'tablefunc')
    pgsql.request_roles('weebl')


def setup_weebl_gunicorn_service():
    render(
        source="weebl-gunicorn.service",
        target="/lib/systemd/system/weebl-gunicorn.service",
        context={})
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


def create_default_user():
    username = "CanonicalOilCiBot"
    email = "oil-ci-bot@canonical.com"
    provider = "ubuntu"
    uid = "oil-ci-bot"
    hookenv.log('Setting up {} as the default user...'.format(username))
    apikey = str(uuid4()).replace('-', str(randint(0, 9) * 2)) # 40 char key
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin preseed_default_superuser \"{}\"".format(
        username, email, provider, uid, apikey)
    try:
        check_call(shlex.split(command))
    except CalledProcessError:
        err_msg = "Error setting up default user"
        hookenv.log(err_msg)


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


def install_weebl(*args, **kwargs):
    weebl_ready = False
    if install_weebl_deb():
        weebl_ready = install_npm_deps()
    setup_weebl_gunicorn_service()
    cmd_service('start', 'weebl-gunicorn')
    cmd_service('restart', 'nginx')
    load_fixtures()
    setup_weebl_site(config['weebl_name'])
    create_default_user
    if weebl_ready:
        set_state('weebl.available')
    else:
        hookenv.status_set('maintenance', 'Weebl installation failed')


def render_config(pgsql):
    db_settings = {
        'host':  pgsql.host(),
        'port': pgsql.port(),
        'database': pgsql.database(),
        'user': pgsql.user(),
        'password': pgsql.password(),
    }
    config = {
        'database': db_settings,
        'static_root': JSLIBS_DIR,
    }
    mkdir_p('/etc/weebl/')
    with open('/etc/weebl/weebl.yaml', 'w') as weebl_db:
        weebl_db.write(yaml.dump(config))


@when('database.database.available', 'nginx.available')
def setup_database(pgsql):
    hookenv.log('Configuring weebl db!')
    hookenv.status_set('maintenance', 'weebl is connecting to pgsql!')
    render_config(pgsql)
    install_weebl()
    hookenv.status_set('active', 'Ready')
