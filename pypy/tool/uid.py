import sys
HUGEINT = (sys.maxint + 1L) * 2L

def uid(obj):
    """
    Return the id of an object as an unsigned number so that its hex
    representation makes sense
    """
    rval = id(obj)
    if rval < 0:
        rval += HUGEINT
    return rval
