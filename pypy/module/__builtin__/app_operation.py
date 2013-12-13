def bin(x):
    if isinstance(x, (int, long)):
        value = x
    elif hasattr(x, '__index__'):
        value = x.__index__()
    else:
        raise TypeError("object cannot be interpreted as an index")
    return value.__format__("#b")
