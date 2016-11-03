#!/usr/bin/env python3

import sys
import apt
from apt.cache import LockFailedException
from lib.charms.layer.weebl import utils


TARBALL_GEN_DEB_PKGS = [
    "libffi-dev",
    "npm"]


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


def main():
    update_debs_if_necessary()
    utils.generate_pip_wheels()
    utils.generate_npm_packs()
    # So no need for sudo next time if root this time:
    utils.recursive_chown_from_root("~/.npm")


if __name__ == '__main__':
    main()
