#!/usr/bin/env python3

import os
import sys
import apt
import yaml
import shutil
from subprocess import check_call
from apt.cache import LockFailedException


TARBALL_GEN_DEB_PKGS = [
    "libffi-dev",
    "npm"]

def get_pip_pkgs(pip_list="./lib/charms/layer/weebl/wheels.yaml"):
    with open(pip_list, 'r') as f:
        return yaml.load(f.read())


def get_npm_pkgs(npm_list="./lib/charms/layer/weebl/npms.yaml"):
    with open(npm_list, 'r') as f:
        return yaml.load(f.read())


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
        shutil.chown(path=path, user=os.environ.get('USER'))


def generate_pip_wheels():
    pip_pkgs = get_pip_pkgs()
    generate_local_pkgs("./wheels/", pip_pkgs, "pip3 wheel {}")


def generate_npm_packs():
    npm_pkgs = get_npm_pkgs()
    generate_local_pkgs("./npms/", npm_pkgs, "npm pack {}")


def main():
    update_debs_if_necessary()
    generate_pip_wheels()
    generate_npm_packs()


if __name__ == '__main__':
    main()
