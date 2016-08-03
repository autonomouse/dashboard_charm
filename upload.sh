#!/bin/bash -ex
# Should be run from top of source tree

rm -fr .temp
[[ -n "$(bzr status | grep -v shelve)" ]] && echo "Repo not clean" && exit 1
mkdir -p .temp/builds
bzr checkout lp:~oil-ci/oil-ci/charm-weebl-BUILT .temp/builds/weebl
charm build -o .temp
rm -fr .temp/builds/weebl/.temp
log=$(bzr log -r-1 --line)
cd .temp/builds/weebl
bzr commit -am "$log"
rm -fr .temp
