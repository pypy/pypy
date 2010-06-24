
try:
    # Preferred way since python 2.6
    from hashlib import md5
except ImportError:
    try:
        from md5 import md5
    except ImportError:
        # no _md5 module on this platform. Try hard to find a pure-python one
        # by fishing it from lib_pypy
        from pypy.tool.lib_pypy import import_from_lib_pypy
        md5 = import_from_lib_pypy('md5')
        del import_from_lib_pypy
