from pypy.rpython.ootypesystem import ootype

_iter_types = {}

def iterator_type(r_iterable, key=None):
    if key is None:
        key = r_iterable.lowleveltype
    else:
        key = key
    if _iter_types.has_key(key):
        return _iter_types[key]
    else:
        ITER = ootype.Instance("Iterator", ootype.ROOT,
                {"iterable": r_iterable.lowleveltype, "index": ootype.Signed})
        _iter_types[key] = ITER
        return ITER
