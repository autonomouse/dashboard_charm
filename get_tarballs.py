#!/usr/bin/env python3

import os
import sys
import apt
from apt.cache import LockFailedException
from lib.charms.layer.weebl import constants
from subprocess import check_output, check_call


def update_debs():
    cache = apt.cache.Cache()
    try:
        cache.update()
        cache.open()
    except LockFailedException:
        sys.exit("\nPlease run again as sudo\n")

    for pkg_name in constants.DEB_PKGS:
        pkg = cache[pkg_name]
        if not pkg.is_installed:
            pkg.mark_install()
            cache.commit()


def custom_update(directory, pks, cmd):
    original_wd = os.getcwd()
    sudo_id = os.environ.get('SUDO_ID', 1000)
    sudo_gid = os.environ.get('SUDO_GID', 1000)
    path = os.path.abspath(directory)
    if not os.path.exists(path):
        os.mkdir(path)
    try:
        os.chdir(path)
        for pkg in pkgs:
            check_output(cmd.format(pkg), shell=True)
    finally:
        os.chdir(original_wd)
        check_call("sudo chown -R {}:{} {}".format(
            sudo_id, sudo_gid, path), shell=True)


def update_pip():
    custom_update(constants.PIPDIR, constants.PIP_PKGS, "pip3 wheel {}")


def update_npm():
    custom_update(constants.NPMDIR, constants.NPM_PKGS, "sudo npm pack {}")


def main():
    update_debs()
    update_pip()
    update_npm()


if __name__ == '__main__':
    main()
