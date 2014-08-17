def negate(f):
    """Create a function which calls `f` and negates its result.  When the
    result is ``space.w_NotImplemented``, ``space.w_NotImplemented`` is
    returned. This is useful for complementing e.g. the __ne__ descriptor if
    your type already defines a __eq__ descriptor.
    """
    def _negator(self, space, w_other):
        # no need to use space.is_ / space.not_
        tmp = f(self, space, w_other)
        if tmp is space.w_NotImplemented:
            return space.w_NotImplemented
        return space.newbool(tmp is space.w_False)
    _negator.func_name = 'negate-%s' % f.func_name
    return _negator

def get_positive_index(where, length):
    if where < 0:
        where += length
        if where < 0:
            where = 0
    elif where > length:
        where = length
    assert where >= 0
    return where
