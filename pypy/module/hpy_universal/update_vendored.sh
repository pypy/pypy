#!/bin/bash

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/hpy"
    exit 1
fi

DIR=$(dirname $0)
VENDORED=$DIR/test/_vendored
HPY=$1

echo "status of the repo $HPY:"
git -C "$HPY" --no-pager log --oneline -n 1
git -C "$HPY" describe --abbrev --always --dirty

cp -R "$HPY"/hpy-api/hpy_devel/include/* "$VENDORED/include"
#cp $HPY/test/support.py $VENDORED/

