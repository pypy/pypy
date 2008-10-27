
try:
    # Preferred way since python 2.6
    from hashlib import md5
except ImportError:
    try:
        from md5 import md5
    except ImportError:
        # no _md5 module on this platform
        from pypy.lib.md5 import md5
