def uid(obj):
    rval = id(obj)
    if rval < 0:
        rval += 1L << 32
    return rval
