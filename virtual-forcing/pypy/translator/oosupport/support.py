NT_OS = dict(
    O_RDONLY = 0x0000,
    O_WRONLY = 0x0001,
    O_RDWR   = 0x0002,
    O_APPEND = 0x0008,
    O_CREAT  = 0x0100,
    O_TRUNC  = 0x0200,
    O_TEXT   = 0x4000,
    O_BINARY = 0x8000
    )

def _patch_os(defs=None):
    """
    Modify the value of some attributes of the os module to be sure
    they are the same on every platform pypy is compiled on. Returns a
    dictionary containing the original values that can be passed to
    patch_os to rollback to the original values.
    """
    
    import os
    if defs is None:
        defs = NT_OS
    olddefs = {}
    for name, value in defs.iteritems():
        try:
            olddefs[name] = getattr(os, name)
        except AttributeError:
            pass
        setattr(os, name, value)
    return olddefs

def patch_os():
    return _patch_os()

def unpatch_os(olddefs):
    _patch_os(olddefs)
