def _remove_dead_weakref(d, key):
    from __pypy__ import delitem_if_value_is
    try:
        wr = d[key]
    except KeyError:
        pass
    else:
        if wr() is None:
            delitem_if_value_is(d, key, wr)
