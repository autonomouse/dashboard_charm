#!/usr/bin/env python3

import os
import yaml
import errno
import shlex
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
    command = "systemctl {} {}".format(cmd, service)
    hookenv.log(command)
    check_call(shlex.split(command))


def chown(owner, path):
    chown_cmd = "chown {} {}".format(owner, path)
    check_call(shlex.split(chown_cmd))


def fix_bundle_dir_permissions():
    chown("www-data", "{}/img/bundles/".format(JSLIBS_DIR))


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
        command = "npm install --prefix {} {}".format(JSLIBS_DIR, npm_path)
        check_call(shlex.split(command))
        hookenv.log("Installed {} via npm".format(npm_path))
    return True


def install_pip_deps():
    hookenv.log('Installing pip packages...')
    for pip_path in glob(os.path.join(PIP_DIR, '*')):
        install_cmd = 'pip3 install -U --no-index -f {} {}'.format(
            PIP_DIR, pip_path)
        check_call(shlex.split(install_cmd))
    return True


def setup_weebl_site(weebl_name):
    hookenv.log('Setting up weebl site...')
    command = "django-admin set_up_site \"{}\"".format(weebl_name)
    check_call(shlex.split(command))


def load_fixtures():
    hookenv.log('Loading fixtures...')
    command = "django-admin loaddata initial_settings.yaml"
    check_call(shlex.split(command))


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


def add_ppa(config):
    hookenv.log('Adding ppa')
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    try:
        add_source(ppa, ppa_key)
    except Exception:
        hookenv.log("Unable to add source PPA: {}".format(ppa))


def install_deb_from_ppa(weebl_pkg, config):
    add_ppa(config)
    return install_deb(weebl_pkg)


def install_debs(weebl_pkg, config):
    install_deb_from_ppa(weebl_pkg, config)
    for deb_pkg in NON_WEEBL_DEB_PKGS:
        install_deb(deb_pkg)
    return True


def install_weebl(config):
    hookenv.status_set('maintenance', 'Installing Weebl...')
    weebl_ready = False
    deb_pkg_installed = install_debs(WEEBL_PKG, config)
    npm_pkgs_installed = install_npm_deps()
    pip_pkgs_installed = install_pip_deps()
    if deb_pkg_installed and npm_pkgs_installed and pip_pkgs_installed:
        weebl_ready = True
    setup_weebl_gunicorn_service(config)
    cmd_service('start', 'weebl-gunicorn')
    cmd_service('restart', 'nginx')
    setup_weebl_site(config['username'])
    fix_bundle_dir_permissions()
    if not weebl_ready:
        hookenv.status_set('maintenance', 'Weebl installation failed')
        msg = ('Weebl installation failed: \ndeb pkgs installed: {},\n '
               'npm pkgs installed: {}, \npip pkgs installed: {}')
        raise Exception(msg.format(
            deb_pkg_installed, npm_pkgs_installed, pip_pkgs_installed))
    load_fixtures()
    hookenv.status_set('active', 'Ready')
    set_state('weebl.ready')
    return weebl_ready


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
