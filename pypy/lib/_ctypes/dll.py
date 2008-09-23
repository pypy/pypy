import _rawffi

def dlopen(name, mode):
    # XXX mode is ignored
    if name is None:
        return None # XXX this should return *all* loaded libs, dlopen(NULL)
    return _rawffi.CDLL(name)
