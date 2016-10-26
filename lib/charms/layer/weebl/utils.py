#!/usr/bin/env python3

import os
import errno
import shlex
from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
    )
from random import choice
from string import hexdigits
from charmhelpers.core import hookenv
from subprocess import check_call, check_output, CalledProcessError
from charms.layer.weebl import constants


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


def fix_bundle_dir_permissions():
    chown_cmd = "chown www-data {}/img/bundles/".format(constants.JSLIBS_DIR)
    check_call(shlex.split(chown_cmd))


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
        pkg_path = os.path.join(constants.NPMDIR, npm_pkg.replace('@', '-')
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
    install_cmd = "pip3 install -U --no-index -f {} {}".format(
        constants.PIPDIR, wheel)
    failed = False
    for wheel in constants.PIP_PKGS:
        install_cmd = "pip3 install -U --no-index -f {} {}".format(
            constants.PIPDIR, wheel)
        try:
            check_call(shlex.split(install_cmd))
        except CalledProcessError:
            err_msg = "Failed to install the '{}' wheel via pip".format(wheel)
            hookenv.log(err_msg)
            failed = True
    return False if failed else True
