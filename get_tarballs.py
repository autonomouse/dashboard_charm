#!/usr/bin/env python3

import os
import sys
import apt
import shutil
from apt.cache import LockFailedException
from lib.charms.layer.weebl import constants
from subprocess import check_output, check_call


def install_debs(requires_installation):
    try:
        cache.update()
        cache.open()
    except LockFailedException:
        sys.exit("\nPlease run again as sudo\n")

    for pkg_name in requires_installation:
        pkg = cache[pkg_name]
        pkg.mark_install()
        cache.commit()


def update_debs_if_necessary():
    cache = apt.cache.Cache()
    requires_installation = []
    for pkg_name in constants.DEB_PKGS:
        pkg = cache[pkg_name]
        if not pkg.is_installed:
            requires_installation.append(pkg)
    if requires_installation:
        install_debs(requires_installation)


def chown(path):
    sudo_id = os.environ.get('SUDO_ID', 1000)
    sudo_gid = os.environ.get('SUDO_GID', 1000)
    check_call("chown -R {}:{} {}".format(
        sudo_id, sudo_gid, path), shell=True)


def custom_update(directory, pkgs, cmd):
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
            check_output(cmd.format(pkg), shell=True)
    finally:
        os.chdir(original_wd)
        chown(path)


def update_pip():
    custom_update(constants.PIPDIR, constants.PIP_PKGS, "pip3 wheel {}")


def update_npm():
    custom_update(constants.NPMDIR, constants.NPM_PKGS, "npm pack {}")
    chown("~/.npm") # So don't always need to run with sudo


def main():
    update_debs_if_necessary()
    update_pip()
    update_npm()


if __name__ == '__main__':
    main()
