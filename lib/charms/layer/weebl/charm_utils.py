#!/usr/bin/env python3

import os
import sys
from charms.reactive import set_state
from charmhelpers.core import hookenv
from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
    )
from charmhelpers.core.templating import render
sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))
from charms.layer.weebl import utils


WEEBL_PKG = "python3-weebl"
NON_WEEBL_DEB_PKGS = [
    "postgresql-client",
    "python3-psycopg2"]


def add_ppa(config):
    hookenv.log('Adding ppa')
    ppa = config['ppa']
    ppa_key = config['ppa_key']
    try:
        add_source(ppa, ppa_key)
    except Exception:
        hookenv.log("Unable to add source PPA: {}".format(ppa))


def install_deb_from_ppa(weebl_pkg, config):
    add_ppa(config)
    return install_deb(weebl_pkg)


def install_debs(weebl_pkg, config):
    install_deb_from_ppa(weebl_pkg, config)
    for deb_pkg in NON_WEEBL_DEB_PKGS:
        install_deb(deb_pkg)
    return True


def install_weebl(config):
    hookenv.status_set('maintenance', 'Installing Weebl...')
    weebl_ready = False
    deb_pkg_installed = install_debs(WEEBL_PKG, config)
    npm_pkgs_installed = utils.install_npm_deps()
    pip_pkgs_installed = utils.install_pip_deps()
    if deb_pkg_installed and npm_pkgs_installed and pip_pkgs_installed:
        weebl_ready = True
    setup_weebl_gunicorn_service(config)
    utils.cmd_service('start', 'weebl-gunicorn')
    utils.cmd_service('restart', 'nginx')
    utils.setup_weebl_site(config['username'])
    utils.fix_bundle_dir_permissions()
    if not weebl_ready:
        hookenv.status_set('maintenance', 'Weebl installation failed')
        msg = ('Weebl installation failed: \ndeb pkgs installed: {},\n '
               'npm pkgs installed: {}, \npip pkgs installed: {}')
        raise Exception(msg.format(
            deb_pkg_installed, npm_pkgs_installed, pip_pkgs_installed))
    utils.load_fixtures()
    hookenv.status_set('active', 'Ready')
    set_state('weebl.ready')
    return weebl_ready


def install_deb(pkg):
    hookenv.log('Installing/upgrading {}!'.format(pkg))
    apt_update()
    apt_install([pkg])
    hookenv.log("{} installed!".format(pkg))


def setup_weebl_gunicorn_service(config):
    render(
        source="weebl-gunicorn.service",
        target="/lib/systemd/system/weebl-gunicorn.service",
        context={'extra_options': config['extra_options']})
    utils.cmd_service('enable', 'weebl-gunicorn')
