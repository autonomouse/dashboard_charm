#!/bin/bash
# Should be run from top of source tree

[[ -n "$(bzr status | grep -v shelve)" ]] && echo "Repo not clean" && exit 1
mkdir temp
charm build -o temp
