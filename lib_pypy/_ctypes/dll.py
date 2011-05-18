import _rawffi

def dlopen(name, mode):
    # XXX mode is ignored
    return _rawffi.CDLL(name)
