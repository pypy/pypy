
try:
    import md5
except ImportError:
    # no _md5 module on this platform
    from pypy.lib import md5
