
try:
    # Preferred way since python 2.6
    from hashlib import md5
except ImportError:
    try:
        from md5 import md5
    except ImportError:
        # no _md5 module on this platform. Try hard to find a pure-python one
        # by fishing it from lib_pypy
        from lib_pypy._md5 import new as md5
