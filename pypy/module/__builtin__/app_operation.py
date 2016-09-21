import _operator

def bin(x):
    """Return the binary representation of an integer."""
    value = _operator.index(x)
    return value.__format__("#b")

def oct(x):
    """Return the octal representation of an integer."""
    x = _operator.index(x)
    return x.__format__("#o")

def hex(x):
    """Return the hexadecimal representation of an integer."""
    x = _operator.index(x)
    return x.__format__("#x")
