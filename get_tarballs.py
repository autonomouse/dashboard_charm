#!/usr/bin/env python3

import os
import sys
import apt
import yaml
import shutil
import tempfile
from subprocess import check_call
from apt.cache import LockFailedException


TARBALL_GEN_DEB_PKGS = [
    "libffi-dev",
    "npm"]


def get_pkgs_from_list(pkg_list):
    with open(pkg_list, 'r') as f:
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


def generate_local_pkgs(directory, pkgs, cmd, yaml_file):
    original_wd = os.getcwd()
    path = os.path.abspath(directory)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            shutil.move(yaml_file, tmp)
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
            shutil.move(os.path.join(
                tmp, os.path.basename(yaml_file)), os.path.dirname(yaml_file))
            shutil.chown(path=path, user=os.environ.get('USER'))


def generate_pip_wheels():
    yaml_file = "./wheels/wheels.yaml"
    pip_pkgs = get_pkgs_from_list(yaml_file)
    generate_local_pkgs("./wheels/", pip_pkgs, "pip3 wheel {}", yaml_file)


def generate_npm_pkgs():
    npm_dir = "./npms/"
    yaml_file = os.path.join(npm_dir, "npms.yaml")
    npm_pkgs = get_pkgs_from_list(yaml_file)
    generate_local_pkgs(npm_dir, npm_pkgs, "npm pack {}", yaml_file)
    shrinkwrap(npm_dir)


def shrinkwrap(directory):
    original_wd = os.getcwd()
    path = os.path.abspath(directory)
    tgzs = [tgz for tgz in next(os.walk(path))[2] if tgz.endswith('tgz')]
    try:
        os.chdir(path)
        for tgz in tgzs:
            check_call(["npm", "install", "--prefix", ".", tgz])
        check_call(["npm", "shrinkwrap"])
    finally:
        shutil.rmtree(os.path.join(path, "node_modules"))
        shutil.rmtree(os.path.join(path, "etc"))
        os.chdir(original_wd)


def main():
    update_debs_if_necessary()
    generate_pip_wheels()
    generate_npm_pkgs()


if __name__ == '__main__':
    main()
