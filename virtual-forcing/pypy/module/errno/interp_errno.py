import errno

def get_errorcode(space):
    return space.wrap(errno.errorcode)

