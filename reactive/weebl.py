#!/usr/bin/env python3
import os
import errno
import yaml
import shlex

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


@hook('db-relation-joined')
def request_db(pgsql):
    pgsql.change_database_name('bugs_database')
    pgsql.request_roles('weebl')


def install_pip_deps():
    # TODO: remove pip usage once weebl drops swagger.
    hookenv.log('Installing pip packages!')
    pip_packages = ["django-tastypie-swagger", "django-extensions"]
    command = "python3 -m pip install"
    check_call(shlex.split(command) + pip_packages)


def setup_weebl_gunicorn_service():
    render(
        source="weebl-gunicorn.service",
        target="/lib/systemd/system/weebl-gunicorn.service",
        context={})
    command = "systemctl enable weebl-gunicorn"
    check_call(shlex.split(command))


@hook('config-changed')
@when('weebl.available')
def update_weebl():
    install_weebl_deb()  # update pkg
    # collect_static() and migrate_db() now done in weebl pkg postinst script
    restart_weebl_gunicorn_service()


def restart_weebl_gunicorn_service():
    command = "systemctl restart weebl-gunicorn"
    check_call(shlex.split(command))


def install_weebl_deb():
    hookenv.log('Installing/upgrading weebl!')
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    add_source(ppa, ppa_key)
    apt_update()
    apt_install([weebl_pkg])


def collect_static():
    hookenv.log('Collecting static files...')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin collectstatic --noinput"
    check_call(shlex.split(command))


def setup_weebl_site(weebl_url, weebl_name):
    hookenv.log('Setting up weebl site...')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin set_up_site \"{}\" \"{}\"".format(
        weebl_url, weebl_name)
    try:
        check_call(shlex.split(command))
    except CalledProcessError:
        err_msg = "Error setting up weebl"
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
    hookenv.log('Installing npm packages...')
    mkdir_p(JSLIBS_DIR)
    npm_packages = ["d3", "nvd3", "angular-nvd3"]
    command = ["npm", "install", "--prefix", JSLIBS_DIR] + npm_packages
    check_call(command)


def install_weebl(*args, **kwargs):
    install_weebl_deb()
    install_pip_deps()
    collect_static()
    install_npm_deps()
    setup_weebl_gunicorn_service()
    migrate_db()
    check_call(['service', 'weebl-gunicorn', 'start'])
    check_call(['service', 'nginx', 'restart'])
    hookenv.log('Loading fixtures...')
    load_fixtures()
    weebl_url = config['weebl_url']
    weebl_name = config['weebl_name']
    setup_weebl_site(weebl_url, weebl_name)
    set_state('weebl.available')

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
        'static_root': '/var/lib/weebl/static',
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
