
def resolve_addr(addr):
    import sys
    if not sys.platform.startswith('linux'):
        return None
    from _pypy_remote_debug import _symbolify
    name, filename = _symbolify(addr)
    return name, 0, filename
