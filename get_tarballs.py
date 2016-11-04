#!/usr/bin/env python3

import os
import sys
import apt
import shutil
from subprocess import check_call
from apt.cache import LockFailedException


TARBALL_GEN_DEB_PKGS = [
    "libffi-dev",
    "npm"]
NPM_PKGS = [
    "angular@1.5.8",
    "d3@3.5.17",
    "nvd3@1.8.3",
    "angular-nvd3@1.0.7"]
PIP_PKGS = ["WeasyPrint"]


def install_debs(requires_installation, cache):
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
    for pkg_name in TARBALL_GEN_DEB_PKGS:
        pkg = cache[pkg_name]
        if not pkg.is_installed:
            requires_installation.append(pkg)
    if requires_installation:
        install_debs(requires_installation, cache)


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
    generate_local_pkgs("./wheels/", PIP_PKGS, "pip3 wheel {}")


def generate_npm_packs():
    generate_local_pkgs("./npms/", NPM_PKGS, "npm pack {}")


def recursive_chown_from_root(path):
    sudo_id = os.environ.get('SUDO_ID', 1000)
    sudo_gid = os.environ.get('SUDO_GID', 1000)
    check_call("chown -R {}:{} {}".format(sudo_id, sudo_gid, path), shell=True)


def main():
    update_debs_if_necessary()
    generate_pip_wheels()
    generate_npm_packs()
    # So no need for sudo next time if root this time:
    recursive_chown_from_root("~/.npm")


if __name__ == '__main__':
    main()
