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
    from select import poll, POLLIN, POLLOUT, POLLPRI
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
        ret = dict(p.poll(int(timeout * 1000)))
    else:
        ret = dict(p.poll())

    iretd = [ f for f in iwtd if ret.get(fddict[id(f)], 0) & POLLIN]
    oretd = [ f for f in owtd if ret.get(fddict[id(f)], 0) & POLLOUT]
    eretd = [ f for f in ewtd if ret.get(fddict[id(f)], 0) & POLLPRI]

    return iretd, oretd, eretd
    
