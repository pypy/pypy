
def _conv_descriptor(f):
    if hasattr(f, "fileno"):
        return f.fileno()
    elif isinstance(f, (int, long)):
        return f
    else:
        raise TypeError, "argument must be an int, or have a fileno() method."
