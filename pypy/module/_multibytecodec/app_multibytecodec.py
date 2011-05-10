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
        raise NotImplementedError(
            "MultibyteIncrementalEncoder not supported; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")

class MultibyteIncrementalDecoder(object):
    def __init__(self, *args, **kwds):
        raise NotImplementedError(
            "MultibyteIncrementalDecoder not supported; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")

class MultibyteStreamReader(object):
    def __init__(self, *args, **kwds):
        raise NotImplementedError(
            "MultibyteStreamReader not supported; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")

class MultibyteStreamWriter(object):
    def __init__(self, *args, **kwds):
        raise NotImplementedError(
            "MultibyteStreamWriter not supported; "
            "see pypy/module/_multibytecodec/app_multibytecodec.py")
