#!/usr/bin/env python3

import os
import yaml
import errno
import shutil
from glob import glob
from random import choice
from string import hexdigits
from datetime import datetime
from subprocess import check_call
from distutils.dir_util import copy_tree
from charms.reactive import set_state
from charmhelpers.core import hookenv
from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
    )
from charmhelpers.core.templating import render


os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
WEEBL_YAML = '/etc/weebl/weebl.yaml'
WEEBL_PKG = "python3-weebl"
NON_WEEBL_DEB_PKGS = [
    "postgresql-client",
    "python3-psycopg2"]
PIP_DIR = "./wheels/"
NPM_DIR = "./npms/"
JSLIBS_DIR = "/var/lib/weebl/static"
SVG_DIR = os.path.join(JSLIBS_DIR, "img/bundles")


def mkdir_p(directory_name):
    try:
        os.makedirs(directory_name)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(directory_name):
            raise exc


def cmd_service(cmd, service):
    command = ['systemctl', cmd, service]
    hookenv.log(command)
    check_call(command)


def fix_bundle_dir_permissions():
    shutil.chown(path="{}/img/bundles/".format(JSLIBS_DIR), user="www-data")


def get_or_generate_apikey(apikey):
    if apikey not in [None, "", "None"]:
        hookenv.log("Using apikey already provided.")
        return apikey
    else:
        hookenv.log("No apikey provided - generating random apikey.")
        return ''.join([choice(hexdigits[:16]) for _ in range(40)])


def install_npm_deps():
    hookenv.log('Installing npm packages...')
    mkdir_p(JSLIBS_DIR)
    for npm_path in glob(os.path.join(NPM_DIR, '*')):
        msg = "Installing {} via npm".format(npm_path)
        hookenv.status_set('maintenance', msg)
        hookenv.log(msg)
        command = ['npm', 'install', '--prefix', JSLIBS_DIR, npm_path]
        check_call(command)


def install_pip_deps():
    hookenv.log('Installing pip packages...')
    for pip_path in glob(os.path.join(PIP_DIR, '*')):
        msg = "Installing {} via pip".format(pip_path)
        hookenv.status_set('maintenance', msg)
        hookenv.log(msg)
        check_call([
            'pip3', 'install', '-U', '--no-index', '-f', PIP_DIR, pip_path])


def setup_weebl_site(weebl_name):
    hookenv.log('Setting up weebl site...')
    check_call(['django-admin', 'set_up_site', '"weebl_name"'])


def load_fixtures():
    hookenv.log('Loading fixtures...')
    check_call(['django-admin', 'loaddata', 'initial_settings.yaml'])


def generate_timestamp(timestamp_format="%F_%H-%M-%S"):
    return datetime.now().strftime(timestamp_format)


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
    mkdir_p(os.path.dirname(WEEBL_YAML))
    with open(WEEBL_YAML, 'w') as weebl_db:
        weebl_db.write(yaml.dump(db_config))


def get_weebl_data():
    return yaml.load(open(WEEBL_YAML).read())['database']


def install_deb_from_ppa(weebl_pkg, config):
    hookenv.log('Adding ppa')
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    add_source(ppa, ppa_key)
    install_deb(weebl_pkg)


def install_debs(weebl_pkg, config):
    hookenv.status_set('maintenance', 'Installing Weebl package')
    install_deb_from_ppa(weebl_pkg, config)
    for deb_pkg in NON_WEEBL_DEB_PKGS:
        hookenv.status_set('maintenance', 'Installing ' + deb_pkg + ' package')
        install_deb(deb_pkg)


def install_weebl(config):
    install_debs(WEEBL_PKG, config)
    install_npm_deps()
    install_pip_deps()
    setup_weebl_gunicorn_service(config)
    cmd_service('start', 'weebl-gunicorn')
    cmd_service('restart', 'nginx')
    setup_weebl_site(config['username'])
    fix_bundle_dir_permissions()
    load_fixtures()
    hookenv.status_set('active', 'Ready')
    set_state('weebl.ready')


def install_deb(pkg):
    hookenv.log('Installing/upgrading {}!'.format(pkg))
    apt_update()
    apt_install([pkg])
    hookenv.log("{} installed!".format(pkg))


def setup_weebl_gunicorn_service(config):
    render(
        source="weebl-gunicorn.service",
        target="/lib/systemd/system/weebl-gunicorn.service",
        context={'extra_options': config['extra_options']})
    cmd_service('enable', 'weebl-gunicorn')


def backup_testrun_svgs(parent_dir):
    hookenv.log("Copying test run svgs")
    destination = os.path.join(parent_dir, 'bundles/')
    copy_tree(SVG_DIR, destination)
    hookenv.log("Bundle images (SVGs) copied to {}".format(destination))


def add_testrun_svgs_to_bundles_dir(source):
    mkdir_p(SVG_DIR)
    bundles = os.path.join(source, 'weebl_data/bundles')
    copy_tree(bundles, SVG_DIR)
    hookenv.log("Bundle images (SVGs) copied into {}".format(SVG_DIR))


def remote_db_cli_interaction(app, weebl_data, custom=''):
    os.environ['PGPASSWORD'] = weebl_data['password']
    base_cmd = [app, '-h', weebl_data['host'], '-U', weebl_data['user'], '-p',
                weebl_data['port']]
    base_cmd.extend(custom)
    return check_call(base_cmd)


def save_database_dump(weebl_data, output_file):
    custom = ['-f', 'output_file', '--no-owner', '--no-acl', '-x', '-F', 't',
              '-d', weebl_data['database']]
    remote_db_cli_interaction("pg_dump", weebl_data, custom)


def drop_database(weebl_data, database):
    remote_db_cli_interaction("dropdb", weebl_data, [database])


def create_empty_database(weebl_data, database, postgres_user="postgres"):
    create_cmds = [database, '-O', postgres_user]
    remote_db_cli_interaction("createdb", weebl_data, create_cmds)


def upload_database_dump(weebl_data, dump_file):
    restore_cmds = ['-d', weebl_data['database'], '--clean', '--exit-on-error',
                    dump_file]
    remote_db_cli_interaction("pg_restore", weebl_data, restore_cmds)
