#!/bin/bash -ex
# Should be run from top of source tree

[[ -n "$(bzr status | grep -v shelve)" ]] && echo "Repo not clean" && exit 1
userstr=$(charm whoami | grep "User")
stringarray=($userstr)
echo Logged in as ${stringarray[1]}
charm build
charm push builds/weebl/ weebl
bzr checkout lp:~oil-ci/oil-ci/charm-weebl-BUILT builds/weebl-built
cp -R builds/weebl-built/.bzr builds/weebl/
rm -fr builds/weebl-built/builds
log=$(bzr log -r-1 --line)
cd builds/weebl
bzr add
bzr commit -m "$log"
cd ../..
rm -fr builds deps
