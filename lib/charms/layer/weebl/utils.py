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
from charms.layer.weebl.constants import JSLIBS_DIR, NPM_PKGS


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
    chown_cmd = "chown www-data {}/img/bundles/".format(JSLIBS_DIR)
    check_call(shlex.split(chown_cmd))


def get_or_generate_apikey(apikey):
    if apikey not in [None, "", "None"]:
        hookenv.log("Using apikey already provided.")
        return apikey
    else:
        hookenv.log("No apikey provided - generating random apikey.")
        return ''.join([choice(hexdigits[:16]) for _ in range(40)])


def install_npm_deps(config):
    weebl_ready = True
    hookenv.log('Installing npm packages...')
    mkdir_p(JSLIBS_DIR)
    http_proxy = config['http_proxy']
    https_proxy = config['https_proxy']
    try:
        if http_proxy is not '':
            command = "npm config set proxy {}".format(
                http_proxy)
            check_call(shlex.split(command))
        if https_proxy is not '':
            command = "npm config set https-proxy {}".format(
                https_proxy)
            check_call(shlex.split(command))
    except CalledProcessError:
        err_msg = "Setup of Weebl's NPM proxy failed"
        hookenv.log(err_msg)
        weebl_ready = False
        raise Exception("Setup of Weebl's NPM proxy failed")
    for npm_pkg in NPM_PKGS:
        command = "npm install --prefix {} {}".format(
            JSLIBS_DIR, npm_pkg)
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
    install_cmd = 'pip3 install -U --no-index -f wheels -r wheels/wheels.txt'
    try:
        check_call(shlex.split(install_cmd))
    except CalledProcessError:
        err_msg = "Failed to install pip packages"
        hookenv.log(err_msg)
        return False
    return True
