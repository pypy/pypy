#!/bin/bash

set -e

GITLAB="registry.heptapod.net"
TAG="${GITLAB}/pypy/pypy/ci:v1"

docker build --tag "${TAG}" --file "Dockerfile" .

echo -e "run: \n  docker login ${GITLAB}  # first time\n  docker push ${TAG}"