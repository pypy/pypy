import os
from ctypes_configure import dumpcache
from pypy.jit.backend import detect_cpu

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
    from pypy.jit.backend import detect_cpu
    cpumodel = detect_cpu.autodetect_main_model_and_size()
mod = __import__("ctypes_config_cache._%s_%%s_" %% (cpumodel,),
                 None, None, ["*"])
globals().update(mod.__dict__)\
''' % (basename,)
    g.close()
