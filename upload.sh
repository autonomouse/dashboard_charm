#!/bin/bash -ex
# Should be run from top of source tree

[[ -n "$(bzr status | grep -v shelve)" ]] && echo "Repo not clean" && exit 1

function tidy_up () (
    cd $startdir
    rm -fr builds deps
)

startdir=$(pwd)
trap tidy_up ERR

userstr=$(charm whoami | grep "User")
userstringarray=($userstr)
USER=${userstringarray[1]}
echo Logged in as $USER

charm build -o .

output=$(charm push ./builds/weebl/ cs:~oil-charms/weebl)
charmstringarray=($output)
CHARM=${charmstringarray[1]}

while [ ! $# -eq 0 ]
do
    case "$1" in
        --publish_stable | -s)
            pub_output=$(charm publish ${CHARM} --channel stable)
            ;;
        --publish_candidate | -c)
            pub_output=$(charm publish ${CHARM} --channel candidate)
            ;;
        --publish_beta | -b)
            pub_output=$(charm publish ${CHARM} --channel beta)
            ;;
        --publish_edge | -e)
            pub_output=$(charm publish ${CHARM} --channel edge)
            ;;
        --*)
            pub_output=''
            ;;
    esac
    shift
done

pubarray=($pub_output)
CHANNEL=${pubarray[3]}
if [[ -z  $CHANNEL  ]]; then
    MSG="This charm has not been published."
else
    MSG="This charm has been published to ${CHANNEL}"
fi

bzr checkout lp:~oil-ci/oil-ci/charm-weebl-BUILT builds/weebl-built
cp -R builds/weebl-built/.bzr builds/weebl/
rm -fr builds/weebl-built/builds
log=$(bzr log -r-1 --line)
cd builds/weebl
bzr add
bzr commit -m "$log"
cd $startdir
tidy_up
echo $MSG
