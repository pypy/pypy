def long_getattr(i, attr):
    if attr == "__class__":
        return int
    raise AttributeError, ....

def long_long(value):
    return long(value)
