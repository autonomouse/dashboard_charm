#!/bin/bash -ex
# Should be run from top of source tree

[[ -n "$(bzr status | grep -v shelve)" ]] && echo "Repo not clean" && exit 1

userstr=$(charm whoami | grep "User")
userstringarray=($userstr)
USER=${userstringarray[1]}
echo Logged in as $USER

charm build

output=$(charm push builds/weebl/ weebl)
charmstringarray=($output)
CHARM=${charmstringarray[1]}

while [ ! $# -eq 0 ]
do
    case "$1" in
        --publish | -p)
            charm publish $CHARM --channel stable
    esac
    shift
done

bzr checkout lp:~oil-ci/oil-ci/charm-weebl-BUILT builds/weebl-built
cp -R builds/weebl-built/.bzr builds/weebl/
rm -fr builds/weebl-built/builds
log=$(bzr log -r-1 --line)
cd builds/weebl
bzr add
bzr commit -m "$log"
cd ../..
rm -fr builds deps
