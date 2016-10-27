#!/usr/bin/env python3

import os
import errno
import shlex
from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
    )
from glob import glob
from random import choice
from string import hexdigits
from charmhelpers.core import hookenv
from subprocess import check_call, check_output, CalledProcessError
from charms.layer.weebl import constants
from charmhelpers.core.templating import render


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


def django_admin(cmd):
    hookenv.log(cmd)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'weebl.settings'
    command = "django-admin {}".format(cmd)
    try:
        check_call(shlex.split(command))
    except CalledProcessError:
        hookenv.log("Error using \"{}\" with Weebl's django-admin")


def install_deb(pkg, config):
    hookenv.log('Installing/upgrading {}!'.format(pkg))
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    try:
        add_source(ppa, ppa_key)
    except Exception:
        hookenv.log("Unable to add source PPA: {}".format(ppa))
    try:
        apt_update()
    except Exception as e:
        hookenv.log(str(e))
    try:
        apt_install([pkg])
    except Exception as e:
        hookenv.log(str(e))
        return False
    hookenv.log("{} installed!".format(pkg))
    return True


def chown(owner, path):
    chown_cmd = "chown {} {}".format(owner, path)
    check_call(shlex.split(chown_cmd))


def fix_bundle_dir_permissions():
    chown("www-data", "{}/img/bundles/".format(constants.JSLIBS_DIR))


def get_or_generate_apikey(apikey):
    if apikey not in [None, "", "None"]:
        hookenv.log("Using apikey already provided.")
        return apikey
    else:
        hookenv.log("No apikey provided - generating random apikey.")
        return ''.join([choice(hexdigits[:16]) for _ in range(40)])


def install_npm_deps():
    weebl_ready = True
    hookenv.log('Installing npm packages...')
    mkdir_p(constants.JSLIBS_DIR)
    for npm_pkg in constants.NPM_PKGS:
        pkg_path = os.path.join(constants.NPMDIR, npm_pkg.replace('@', '-'))
        command = "npm install --prefix {} {}.tgz".format(
            constants.JSLIBS_DIR, pkg_path)
        try:
            check_call(shlex.split(command))
        except CalledProcessError:
            err_msg = "Failed to install {} via npm".format(npm_pkg)
            hookenv.log(err_msg)
            weebl_ready = False
            raise Exception("Installation of Weebl's NPM dependencies failed")
        msg = "Installed {} via npm".format(npm_pkg)
        hookenv.log(msg)
    return weebl_ready


def install_pip_deps():
    hookenv.log('Installing pip packages...')
    pips_installed = True
    for pip_path in glob(os.path.join(constants.PIPDIR, '*')):
        install_cmd = 'pip3 install -U --no-index -f {} {}'.format(
            constants.PIPDIR, pip_path)
        try:
            check_call(shlex.split(install_cmd))
        except CalledProcessError:
            hookenv.log("Failed to pip install the '{}' wheel".format(pip_pkg))
            pips_installed = False
    return pips_installed


def setup_weebl_gunicorn_service(config):
    render(
        source="weebl-gunicorn.service",
        target="/lib/systemd/system/weebl-gunicorn.service",
        context={'extra_options': config['extra_options']})
    cmd_service('enable', 'weebl-gunicorn')


def setup_weebl_site(weebl_name):
    hookenv.log('Setting up weebl site...')
    django_admin("set_up_site \"{}\"".format(weebl_name))


def load_fixtures():
    hookenv.log('Loading fixtures...')
    django_admin("loaddata initial_settings.yaml")


def install_weebl(config, weebl_pkg):
    hookenv.status_set('maintenance', 'Installing Weebl...')
    weebl_ready = False
    deb_pkg_installed = install_deb(weebl_pkg, config)
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
        msg = ('Weebl installation failed: deb pkgs installed: {}, '
               'npm pkgs installed: {}, pip pkgs installed: {}')
        raise Exception(msg.format(
            deb_pkg_installed, npm_pkgs_installed, pip_pkgs_installed))
    load_fixtures()
    return weebl_ready
