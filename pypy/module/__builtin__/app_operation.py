def bin(x):
    if not isinstance(x, (int, long)):
        raise TypeError("must be int or long")
    return x.__format__("#b")
