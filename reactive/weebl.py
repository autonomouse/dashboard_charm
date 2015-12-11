#!/usr/bin/env python3.5
import os
import errno
import yaml

from subprocess import check_call

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


config = hookenv.config()


def mkdir_p(directory_name):
    try:
        os.makedirs(directory_name)
    except OSError as exc: 
        if exc.errno != errno.EEXIST or not os.path.isdir(directory_name):
            raise exc


@hook('db-relation-joined')
def request_db(pgsql):
    pgsql.change_database_name('bugs_database')
    pgsql.request_roles('weebl')


@hook('config-changed')
def check_admin_pass():
    admin_pass = hookenv.config('admin-pass')
    if admin_pass:
        set_state('admin-pass')
    else:
        remove_state('admin-pass')

JSLIBS_DIR = 'weebl/oilserver/static'


def install_pip_deps():
    pip_packages = ["django-tastypie-swagger", "django-extensions"]
    command = ["python3.4", "-m", "pip", "install"] + pip_packages
    check_call(command)


def install_npm_deps():
    mkdir_p(JSLIBS_DIR)
    npm_packages = ["d3", "nvd3", "angular-nvd3"]
    command = ["npm", "install", "--prefix", JSLIBS_DIR] + npm_packages
    check_call(command)


def setup_weebl_gunicorn_service():
    render(
        source="weebl-gunicorn.service",
        target="/lib/systemd/system/weebl-gunicorn.service",
        context={})
    check_call(['systemctl', 'enable', 'weebl-gunicorn'])


def install_weebl_deb():
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    add_source(ppa, ppa_key)
    apt_update()
    apt_install(['python3-weebl'])


@when('nginx.available')
def install_weebl(*args, **kwargs):
    hookenv.log('Installing weebl!')
    install_weebl_deb()
    hookenv.log('Installing pip packages!')
    install_pip_deps()
    hookenv.log('Installing npm packages!')
    install_npm_deps()
    setup_weebl_gunicorn_service()


def render_db_config(pgsql):
    db_settings = {
        'host':  pgsql.host(),
        'port': pgsql.port(),
        'database': pgsql.database(),
        'user': pgsql.user(),
        'password': pgsql.password(),
    }
    mkdir_p('/etc/weebl/')
    with open('/etc/weebl/weebl-db.yaml', 'w') as weebl_db:
        weebl_db.write(yaml.dump(db_settings))


@when('database.database.available')
def setup_database(pgsql):
    hookenv.log('Configuring weebl db!')
    hookenv.status_set('maintenance', 'weebl is connecting to pgsql!')
    render_db_config(pgsql)
    hookenv.status_set('active', 'Ready')
