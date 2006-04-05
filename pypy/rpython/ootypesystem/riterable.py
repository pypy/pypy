from pypy.rpython.ootypesystem import ootype

_iter_types = {}

def iterator_type(r_iterable):
    key = r_iterable.lowleveltype
    if _iter_types.has_key(key):
        return _iter_types[key]
    else:
        ITER = ootype.Instance("Iterator", ootype.ROOT,
                {"iterable": key, "index": ootype.Signed})
        _iter_types[key] = ITER
        return ITER
