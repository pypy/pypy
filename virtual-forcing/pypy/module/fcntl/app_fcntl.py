
def _conv_descriptor(f):
    if hasattr(f, "fileno"):
        return f.fileno()
    elif isinstance(f, (int, long)):
        return f
    else:
        raise TypeError, "argument must be an int, or have a fileno() method."

__doc__ = """This module performs file control and I/O control on file
descriptors.  It is an interface to the fcntl() and ioctl() Unix
routines.  File descriptors can be obtained with the fileno() method of
a file or socket object."""
