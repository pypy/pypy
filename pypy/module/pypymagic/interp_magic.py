
def pypy_repr(space, w_object):
    return space.wrap('%r' % (w_object,))
