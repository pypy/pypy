#!/bin/bash

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/hpy"
    exit 1
fi

DIR=$(dirname $0)
VENDORED=$DIR/_vendored
VENDORED_TEST=$DIR/test/_vendored
HPY=$1

echo "GIT status of $HPY"
git -C "$HPY" --no-pager log --oneline -n 1
git -C "$HPY" --no-pager diff --stat

echo cp -R "$HPY"/hpy/devel/" $DIR/_vendored/hpy"
cp -R "$HPY"/test/* "$DIR/test/_vendored"

echo
echo
echo "HG status of pypy"
hg st $DIR
