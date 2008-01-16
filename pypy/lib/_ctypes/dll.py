import _rawffi

def dlopen(name, mode):
    # XXX mode is ignored
    if name is None:
        return None # XXX seems to mean the cpython lib
    return _rawffi.CDLL(name)
