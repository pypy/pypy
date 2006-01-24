"""
Helper file for Python equivalents of socket specific calls.
"""

import socket

# HACK: We have to prevent GC to collect the socket object we create within this
# module. Because socket.close() is called on GC this can lead to strange
# effects in corner cases where file descriptors are reused.
socket_cache = {}
keep_sockets_alive = []

class ADDRINFO(object):
    # a simulated addrinfo structure from C, i.e. a chained list
    # returned by getaddrinfo()
    def __init__(self, host, port, family, socktype, proto, flags):
        addrinfo = socket.getaddrinfo(host, port,
                                      family, socktype, proto, flags)
        self._entries = iter(addrinfo)

    def nextinfo(self):
        try:
            info = self._entries.next()
        except StopIteration:
            return [0] * 8

        return info[:-1] + info[-1]

    def free(self):
        pass

def getaddrinfo(host, port, family, socktype, proto, flags):
    return ADDRINFO(host, port, family, socktype, proto, flags)

def newsocket(family, type, protocol):
    s = socket.socket(family, type, protocol)
    fileno = s.fileno()
    if socket_cache.has_key(fileno):
        keep_sockets_alive.append(socket_cache[fileno])
    socket_cache[fileno] = s
    return fileno

def connect(fd, sockname, family):
    s = socket_cache[fd]
    if family == socket.AF_INET:
        s.connect(sockname[:2])
    elif family == socket.AF_INET6:
        s.connect(sockname)

def getpeername(fd):
    s = socket_cache[fd]
    return s.getpeername()

def freesockname(sockname):
    pass
