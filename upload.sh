#!/bin/bash -ex
# Should be run from top of source tree

[[ -n "$(bzr status | grep -v shelve)" ]] && echo "Repo not clean" && exit 1
charm build
bzr checkout lp:~oil-ci/oil-ci/charm-weebl-BUILT builds/weebl-built
cp -R builds/weebl-built/.bzr builds/weebl/
log=$(bzr log -r-1 --line)
cd builds/weebl
bzr commit -am "$log"
rm -fr builds deps
