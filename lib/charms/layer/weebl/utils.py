#!/usr/bin/env python3

import os
import yaml
import errno
import shlex
import shutil
from glob import glob
from random import choice
from string import hexdigits
from datetime import datetime
from subprocess import check_call, CalledProcessError


os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
JSLIBS_DIR = "/var/lib/weebl/static"
NPM_PKGS = [
    "angular@1.5.8",
    "d3@3.5.17",
    "nvd3@1.8.3",
    "angular-nvd3@1.0.7"]
PIPDIR = "./wheels/"
WEEBL_YAML = '/etc/weebl/weebl.yaml'
PIP_PKGS = ["WeasyPrint"]
NPMDIR = "./npms/"


def run_cli(cmd, err_msg=None, shell=False, raise_on_err=False):
    try:
        check_call(cmd, shell=shell)
        return True
    except CalledProcessError:
        if raise_on_err:
            raise Exception(err_msg)
        return False


def mkdir_p(directory_name):
    try:
        os.makedirs(directory_name)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(directory_name):
            raise exc


def cmd_service(cmd, service):
    command = "systemctl {} {}".format(cmd, service)
    run_cli(shlex.split(command))


def chown(owner, path):
    chown_cmd = "chown {} {}".format(owner, path)
    run_cli(shlex.split(chown_cmd))


def recursive_chown_from_root(path):
    sudo_id = os.environ.get('SUDO_ID', 1000)
    sudo_gid = os.environ.get('SUDO_GID', 1000)
    run_cli("chown -R {}:{} {}".format(sudo_id, sudo_gid, path), shell=True)


def fix_bundle_dir_permissions():
    chown("www-data", "{}/img/bundles/".format(JSLIBS_DIR))


def get_or_generate_apikey(apikey):
    if apikey not in [None, "", "None"]:
        return apikey
    else:
        return ''.join([choice(hexdigits[:16]) for _ in range(40)])


def install_npm_deps():
    weebl_ready = True
    mkdir_p(JSLIBS_DIR)
    for npm_pkg in NPM_PKGS:
        pkg_path = os.path.join(NPMDIR, npm_pkg.replace('@', '-'))
        command = "npm install --prefix {} {}.tgz".format(
            JSLIBS_DIR, pkg_path)
        output = run_cli(
            shlex.split(command), raise_on_err=True,
            err_msg="Failed to install {} via npm".format(npm_pkg))
        if not output:
            weebl_ready = False
    return weebl_ready


def install_pip_deps():
    pips_installed = True
    for pip_path in glob(os.path.join(PIPDIR, '*')):
        install_cmd = 'pip3 install -U --no-index -f {} {}'.format(
            PIPDIR, pip_path)
        output = run_cli(
            shlex.split(install_cmd), raise_on_err=False,
            err_msg="Failed to install wheel: '{}'".format(pip_path))
        if not output:
            pips_installed = False
    return pips_installed


def setup_weebl_site(weebl_name):
    command = "django-admin set_up_site \"{}\"".format(weebl_name)
    run_cli(shlex.split(command),
            err_msg="Error using \"{}\" with Weebl's django-admin")


def load_fixtures():
    command = "django-admin loaddata initial_settings.yaml"
    run_cli(shlex.split(command),
            err_msg="Error using \"{}\" with Weebl's django-admin")


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


def generate_local_pkgs(directory, pkgs, cmd):
    original_wd = os.getcwd()
    path = os.path.abspath(directory)
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass
    os.mkdir(path)
    try:
        os.chdir(path)
        for pkg in pkgs:
            check_call(cmd.format(pkg), shell=True)
    finally:
        os.chdir(original_wd)
        recursive_chown_from_root(path)


def generate_pip_wheels():
    generate_local_pkgs(PIPDIR, PIP_PKGS, "pip3 wheel {}")


def generate_npm_packs():
    generate_local_pkgs(NPMDIR, NPM_PKGS, "npm pack {}")
