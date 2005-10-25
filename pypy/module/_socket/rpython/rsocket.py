"""
Helper file for Python equivalents of socket specific calls.
"""

import socket

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
