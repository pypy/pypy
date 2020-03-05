#!/bin/bash

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/hpy"
    exit 1
fi

DIR=$(dirname $0)
VENDORED=$DIR/_vendored
HPY=$1

echo "GIT status of $HPY"
git -C "$HPY" --no-pager log --oneline -n 1
git -C "$HPY" --no-pager diff --stat

cp -R "$HPY"/hpy/devel/include/* "$VENDORED/include"
cp -R "$HPY"/test/* "$VENDORED/test"

echo
echo
echo "HG status of pypy"
hg st $DIR
