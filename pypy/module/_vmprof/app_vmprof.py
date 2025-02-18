
def resolve_addr(addr):
    import sys
    if not sys.platform.startswith('linux'):
        return None
    from _pypy_remote_debug import _symbolify
    res = _symbolify(addr)
    if res is None:
        return None
    name, filename = res
    return name.decode('utf-8'), 0, filename.decode('utf-8')

def resolve_many_addrs(addrs):
    import sys
    if not sys.platform.startswith('linux'):
        return {}
    from _pypy_remote_debug import _symbolify_all
    res = _symbolify_all(addrs)
    return {addr: (name.decode('utf-8'), 0, filename.decode('utf-8')) for addr, (name, filename) in res.items()}
