

def dict_update(d,o):
    for k in o.keys():
        d[k] = o[k]

def dict_popitem(d):
    k = d.keys()[0]
    v = d[k]
    del d[k]
    return k, v

def dict_get(d, k, v=None):
    if d.has_key(k):
        return d[k]
    return v

def dict_setdefault(d, k, v):
    if d.has_key(k):
        return d[k]
    d[k] = v
    return v

class __unique: pass

def dict_pop(d, k, v=__unique):
    if d.has_key(k):
        v = d[k]
        del d[k]
    if v is __unique:
        raise KeyError, k
    return v

def dict_iteritems(d):
    return iter(d.items())

def dict_iterkeys(d):
    return iter(d.keys())

def dict_itervalues(d):
    return iter(d.values())

