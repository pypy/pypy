import os
from ctypes_configure import dumpcache
from rpython.jit.backend import detect_cpu

def dumpcache2(basename, config):
    model = detect_cpu.autodetect_main_model_and_size()
    filename = '_%s_%s_.py' % (basename, model)
    dumpcache.dumpcache(__file__, filename, config)
    #
    filename = os.path.join(os.path.dirname(__file__),
                            '_%s_cache.py' % (basename,))
    g = open(filename, 'w')
    print >> g, '''\
try:
    from __pypy__ import cpumodel
except ImportError:
    from rpython.jit.backend import detect_cpu
    cpumodel = detect_cpu.autodetect_main_model_and_size()
# XXX relative import, should be removed together with
# XXX the relative imports done e.g. by lib_pypy/pypy_test/test_hashlib
mod = __import__("_%s_%%s_" %% (cpumodel,),
                 globals(), locals(), ["*"])
globals().update(mod.__dict__)\
''' % (basename,)
    g.close()
