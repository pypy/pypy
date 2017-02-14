import errno
from rpython.rlib.objectmodel import not_rpython

@not_rpython
def get_errorcode(space):
    return space.wrap(errno.errorcode)

