#! /usr/bin/env python
# Run this script to rebuild all caches from the *.ctc.py files.

import autopath
import os, sys
import py

_dirpath = os.path.dirname(__file__) or os.curdir

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("ctypes_config_cache")
py.log.setconsumer("ctypes_config_cache", ansi_log)


def rebuild_one(name):
    filename = os.path.join(_dirpath, name)
    d = {'__file__': filename}
    path = sys.path[:]
    try:
        sys.path.insert(0, _dirpath)
        execfile(filename, d)
    finally:
        sys.path[:] = path

def try_rebuild():
    for p in os.listdir(_dirpath):
        if p.startswith('_') and (p.endswith('_cache.py') or
                                  p.endswith('_cache.pyc')):
            os.unlink(os.path.join(_dirpath, p))
    for p in os.listdir(_dirpath):
        if p.endswith('.ctc.py'):
            try:
                rebuild_one(p)
            except Exception, e:
                log.ERROR("Running %s:\n  %s: %s" % (
                    os.path.join(_dirpath, p),
                    e.__class__.__name__, e))


if __name__ == '__main__':
    try_rebuild()
