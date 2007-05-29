#!/bin/sh

DISTDIR="/home/burt/projects/pypy/codespeak/pypy/dist"
DEPSDIR="/home/burt/projects/pypy/codespeak/pyontology/pyontology-deps"

export PYTHONPATH="${DEPSDIR}:${DISTDIR}"

exec ${DISTDIR}/pypy/bin/py.py --withmod-thread "$@"