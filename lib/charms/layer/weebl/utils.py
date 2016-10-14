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
from subprocess import check_call, CalledProcessError
from charms.layer.weebl.constants import JSLIBS_DIR, NPM_PKGS


def mkdir_p(directory_name):
    try:
        os.makedirs(directory_name)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(directory_name):
            raise exc


def cmd_service(cmd, service, hookenv=None):
    command = "systemctl {} {}".format(cmd, service)
    if hookenv:
        hookenv.log(command)
    check_call(shlex.split(command))


def install_deb(pkg, config, hookenv=None):
    if hookenv:
        hookenv.log('Installing/upgrading {}!'.format(pkg))
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    try:
        add_source(ppa, ppa_key)
    except Exception:
        if hookenv:
            hookenv.log("Unable to add source PPA: {}".format(ppa))
    try:
        apt_update()
        apt_install([pkg])
    except Exception as e:
        if hookenv:
            hookenv.log(str(e))
        raise Exception('Installation of Weebl deb failed')
    return True


def fix_bundle_dir_permissions():
    chown_cmd = "chown www-data {}/img/bundles/".format(JSLIBS_DIR)
    check_call(shlex.split(chown_cmd))


def get_or_generate_apikey(apikey, hookenv=None):
    if apikey not in [None, "", "None"]:
        if hookenv:
            hookenv.log("Using apikey already provided.")
        return apikey
    else:
        if hookenv:
            hookenv.log("No apikey provided - generating random apikey.")
        return ''.join([choice(hexdigits[:16]) for _ in range(40)])


def install_npm_deps(hookenv=None):
    weebl_ready = True
    if hookenv:
        hookenv.log('Installing npm packages...')
    mkdir_p(JSLIBS_DIR)
    for npm_pkg in NPM_PKGS:
        command = "npm install --prefix {} {}".format(
            JSLIBS_DIR, npm_pkg)
        try:
            check_call(shlex.split(command))
        except CalledProcessError:
            err_msg = "Failed to install {} via npm".format(npm_pkg)
            if hookenv:
                hookenv.log(err_msg)
            weebl_ready = False
            raise Exception("Installation of Weebl's NPM dependencies failed")
        return weebl_ready
