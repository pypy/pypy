def bin(x):
    if not isinstance(x, (int, long)):
        raise TypeError("must be int or long")
    return format(x, "#b")
