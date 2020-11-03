#!/bin/bash

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/hpy"
    exit 1
fi

DIR=$(dirname $0)
HPY=$1

# ~~~ helper functions ~~~

check_dirty() {
    if [[ $(git -C "$HPY" diff --stat) != '' ]]; then
        echo "WARNING! The source hpy repo is dirty"
        echo
    fi
}

check_version_status() {
    # check that the version in hpy/devel/version.py corresponds to the one
    # given by git
    revgit=$(git -C "$HPY" describe --abbrev=7 --dirty --always --tags --long)

    pushd "$HPY/hpy/devel" > /dev/null
    revpy=$(python -c 'import version;print(version.__git_revision__)')
    popd > /dev/null

    if [ "$revgit" != "$revpy" ]
    then
        echo "ERROR: hpy/devel/version.py seems to be outdated"
        echo "  revision reported by git describe: $revgit"
        echo "  revision in hpy/devel/version.py:  $revpy"
        echo
        echo "Please run setup.py build in the hpy repo"
        exit 1
    fi
}

myrsync() {
    rsync --exclude '*~' --exclude '*.pyc' --exclude __pycache__ "$@" 
}

# ~~~ main code ~~~

check_dirty
check_version_status

myrsync -a --delete ${HPY}/hpy/devel/ ${DIR}/_vendored/hpy/devel/
myrsync -a --delete ${HPY}/test/* ${DIR}/test/_vendored/


echo "GIT status of $HPY"
git -C "$HPY" --no-pager log --oneline -n 1
git -C "$HPY" --no-pager diff --stat
echo
echo "HG status of pypy"
hg st $DIR
echo
echo "HPy version"
cat _vendored/hpy/devel/version.py
