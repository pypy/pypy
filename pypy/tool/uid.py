def uid(obj):
    rval = id(obj)
    if rval < 1:
        rval += 1L << 32
    return rval
