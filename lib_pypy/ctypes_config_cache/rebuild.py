#! /usr/bin/env python
# Run this script to rebuild all caches from the *.ctc.py files.

# hack: we cannot directly import autopath, as we are outside the pypy
# package.  However, we pretend to be inside pypy/tool and manually run it, to
# get the correct path
import os.path
this_dir = os.path.dirname(__file__)
autopath_py = os.path.join(this_dir, '../../pypy/tool/autopath.py')
autopath_py = os.path.abspath(autopath_py)
execfile(autopath_py, dict(__name__='autopath', __file__=autopath_py))

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
    from pypy.jit.backend import detect_cpu
    model = detect_cpu.autodetect_main_model_and_size()
    # remove the files '_*_model_.py'
    left = {}
    for p in os.listdir(_dirpath):
        if p.startswith('_') and (p.endswith('_%s_.py' % model) or
                                  p.endswith('_%s_.pyc' % model)):
            os.unlink(os.path.join(_dirpath, p))
        elif p.startswith('_') and (p.endswith('_.py') or
                                    p.endswith('_.pyc')):
            for i in range(2, len(p)-4):
                left[p[:i]] = True
    # remove the files '_*_cache.py' if there is no '_*_*_.py' left around
    for p in os.listdir(_dirpath):
        if p.startswith('_') and (p.endswith('_cache.py') or
                                  p.endswith('_cache.pyc')):
            if p[:-9] not in left:
                os.unlink(os.path.join(_dirpath, p))
    #
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
