# NOT_RPYTHON
#
# These classes are not supported so far.
#
# My theory is that they are not widely used on CPython either, because
# I found two bugs just by looking at their .c source: they always call
# encreset() after a piece of data, even though I think it's wrong ---
# it should be called only once at the end; and mbiencoder_reset() calls
# decreset() instead of encreset().
#

class MultibyteIncrementalEncoder(object):
    def __init__(self, *args, **kwds):
        raise LookupError(
            "MultibyteIncrementalEncoder not implemented; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")

class MultibyteIncrementalDecoder(object):
    def __init__(self, *args, **kwds):
        raise LookupError(
            "MultibyteIncrementalDecoder not implemented; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")

class MultibyteStreamReader(object):
    def __init__(self, *args, **kwds):
        raise LookupError(
            "MultibyteStreamReader not implemented; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")

class MultibyteStreamWriter(object):
    def __init__(self, *args, **kwds):
        raise LookupError(
            "MultibyteStreamWriter not implemented; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")
