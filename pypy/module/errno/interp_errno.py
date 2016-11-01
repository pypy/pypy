import errno

def get_errorcode(space):
    return space.newint(errno.errorcode)

