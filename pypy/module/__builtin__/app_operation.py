def bin(x):
    if not isinstance(x, int):
        raise TypeError("%s object cannot be interpreted as an integer" % type(x))
    return x.__format__("#b")
