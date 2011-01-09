import _rawffi

def dlopen(name, mode):
    # XXX mode is ignored
    if name is None:
        # XXX this should return *all* loaded libs, dlopen(NULL).
        raise NotImplementedError("dlopen(None)")
    return _rawffi.CDLL(name)
