import sys

def uid(obj):
    rval = id(obj)
    if rval < 0:
        rval += (long(sys.maxint)+1)*2
    return rval
