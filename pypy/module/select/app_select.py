class error(Exception):
    pass

def as_fd(f):
    if not isinstance(f, (int, long)):
        try:
            fileno = f.fileno
        except AttributeError:
            raise TypeError("argument must be an int, or have a fileno() method.")
        f = f.fileno()
        if not isinstance(f, (int, long)):
            raise TypeError("fileno() returned a non-integer")
    fd = int(f)
    if fd < 0 or isinstance(fd, long):
        raise ValueError("file descriptor cannot be a negative integer (%i)"%fd)
    return fd

def select(iwtd, owtd, ewtd, timeout=None):
    """Wait until one or more file descriptors are ready for some kind of I/O.
The first three arguments are sequences of file descriptors to be waited for:
rlist -- wait until ready for reading
wlist -- wait until ready for writing
xlist -- wait for an ``exceptional condition''
If only one kind of condition is required, pass [] for the other lists.
A file descriptor is either a socket or file object, or a small integer
gotten from a fileno() method call on one of those.

The optional 4th argument specifies a timeout in seconds; it may be
a floating point number to specify fractions of seconds.  If it is absent
or None, the call will never time out.

The return value is a tuple of three lists corresponding to the first three
arguments; each contains the subset of the corresponding file descriptors
that are ready.

*** IMPORTANT NOTICE ***
On Windows, only sockets are supported; on Unix, all file descriptors.
"""
    from select import poll, POLLIN, POLLOUT, POLLPRI, POLLERR, POLLHUP
    fddict = {}
    polldict = {}
    fd = 0
    for f in iwtd + owtd + ewtd:
        fddict[id(f)] = as_fd(f)
    for f in iwtd:
        fd = fddict[id(f)]
        polldict[fd] = polldict.get(fd, 0) | POLLIN
    for f in owtd:
        fd = fddict[id(f)]
        polldict[fd] = polldict.get(fd, 0) | POLLOUT
    for f in ewtd:
        fd = fddict[id(f)]
        polldict[fd] = polldict.get(fd, 0) | POLLPRI

    p = poll()
    for fd, mask in polldict.iteritems():
        p.register(fd, mask)
    if timeout is not None:
        if (not hasattr(timeout, '__int__') and
            not hasattr(timeout, '__float__')):
            raise TypeError('timeout must be a float or None')
        ret = dict(p.poll(int(float(timeout) * 1000)))
    else:
        ret = dict(p.poll())

    iretd = [ f for f in iwtd if ret.get(fddict[id(f)], 0) & (POLLIN|POLLHUP|POLLERR)]
    oretd = [ f for f in owtd if ret.get(fddict[id(f)], 0) & POLLOUT]
    eretd = [ f for f in ewtd if ret.get(fddict[id(f)], 0) & (POLLERR|POLLPRI)]

    return iretd, oretd, eretd
    
