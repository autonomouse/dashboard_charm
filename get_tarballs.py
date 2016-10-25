#!/usr/bin/env python3

import os
import sys
import apt
from apt.cache import LockFailedException
from lib.charms.layer.weebl import constants
from subprocess import check_output, check_call


original_wd = os.getcwd()
cache = apt.cache.Cache()
sudo_id = os.environ.get('SUDO_ID', 1000)
sudo_gid = os.environ.get('SUDO_GID', 1000)

# Update debs
try:
    cache.update()
    cache.open()
except LockFailedException:
    print("\nPlease run again as sudo\n")
    sys.exit()

for pkg_name in constants.DEB_PKGS:
    pkg = cache[pkg_name]
    if pkg.is_installed:
        print("{pkg_name} already installed".format(pkg_name=pkg_name))
    else:
        pkg.mark_install()
        cache.commit()
print("\n")

# Update pip
pip_path = os.path.abspath(constants.PIPDIR)
if not os.path.exists(pip_path):
    os.mkdir(pip_path)
try:
    os.chdir(pip_path)
    for pip_pkg in constants.PIP_PKGS:
        check_output("pip3 wheel {}".format(pip_pkg), shell=True)
finally:
    os.chdir(original_wd)
    check_call("sudo chown -R {}:{} {}".format(
        sudo_id, sudo_gid, pip_path), shell=True)
print("The following python wheels are now available in {}:\n".format(
    pip_path))
print("\n".join(sorted(os.listdir(pip_path), key=lambda s: s.lower())))
print("\n")

# Update pip
npm_path = os.path.abspath(constants.NPMDIR)
if not os.path.exists(npm_path):
    os.mkdir(npm_path)
try:
    os.chdir(npm_path)
    for npm_pkg in constants.NPM_PKGS:
        check_output("sudo npm pack {}".format(npm_pkg), shell=True)
finally:
    os.chdir(original_wd)
    check_call("sudo chown -R {}:{} {}".format(
        sudo_id, sudo_gid, npm_path), shell=True)
print("The following npm pkgs are now available in {}:\n".format(npm_path))
print("\n".join(sorted(os.listdir(npm_path), key=lambda s: s.lower())))
print("\n")
