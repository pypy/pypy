"""
Helper file for Python equivalents of socket specific calls.
"""

import socket

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
    # HACK: We have to prevent GC to collect the socket object because we don't
    # want it to be closed.
    keep_sockets_alive.append(s)
    return s.fileno()
