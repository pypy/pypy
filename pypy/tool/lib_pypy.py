import os
import sys
from functools import partial

import py
import pypy
import pypy.module
from pypy.module.sys.version import CPYTHON_VERSION


from ctypes_configure import dumpcache
from pypy.jit.backend import detect_cpu


from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("ctypes_config_cache")
py.log.setconsumer("ctypes_config_cache", ansi_log)


LIB_ROOT = py.path.local(pypy.__path__[0]).dirpath()
LIB_PYPY =  LIB_ROOT.join('lib_pypy')
LIB_PYTHON = LIB_ROOT.join('lib-python', '%d.%d' % CPYTHON_VERSION[:2])


ctypes_cachedir = LIB_PYPY.join('ctypes_config_cache')


def dumpcache2(basename, config, sourcefile):
    model = detect_cpu.autodetect_main_model_and_size()
    filename = '_%s_%s_.py' % (basename, model)
    dumpcache.dumpcache(sourcefile, filename, config)
    #
    filename = ctypes_cachedir.join('_%s_cache.py' % (basename))
    filename.write('''\
try:
    from __pypy__ import cpumodel
except ImportError:
    from pypy.jit.backend import detect_cpu
    cpumodel = detect_cpu.autodetect_main_model_and_size()
# XXX relative import, should be removed together with
# XXX the relative imports done e.g. by lib_pypy/pypy_test/test_hashlib
mod = __import__("_BASENAME_%s_" % (cpumodel,),
                 globals(), locals(), ["*"])
globals().update(mod.__dict__)
'''.replace("BASENAME", basename))





def rebuild_one(path):
    filename = str(path)
    d = {'__file__': filename}
    try:
        execfile(filename, d)
    finally:
        base = path.basename.split('.')[0]
        dumpcache2(base, d['config'], filename)


def try_rebuild():
    from pypy.jit.backend import detect_cpu
    model = detect_cpu.autodetect_main_model_and_size()

    # kill pyc files:
    for p in ctypes_cachedir.listdir('*.pyc'):
        p.remove()
        
    # remove the files '_*_model_.py'
    left = {}
    for p in ctypes_cachedir.listdir('_*_%s_.py' % (model,)):
        p.remove()
    # remove the files '_*_cache.py' if there is no '_*_*_.py' left around
    for p in ctypes_cachedir.listdir('_*_cache.py'):
        fnmatch = p.basename.replace('cache', '*')
        if not ctypes_cachedir.listdir(fnmatch):
            p.remove()
    #
    for p in ctypes_cachedir.listdir('*.ctc.py'):
        try:
            rebuild_one(p)
        except Exception, e:
            log.ERROR("Running %s:\n  %s: %s" % (
                LIB_PYPY.bestrelpath(p),
                e.__class__.__name__, e))
            import traceback
            traceback.print_exc()

