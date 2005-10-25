"""
Helper file for Python equivalents of os specific calls.
"""

import socket

class ADDRINFO(object):
    def __init__(self, host, port, family, socktype, proto, flags):
        self._entries = iter(socket.getaddrinfo(
            host, port, family, socktype, proto, flags))
        
    def nextinfo(self):
        try:
            info = self._entries.next()
        except StopIteration:
            return None
        (self.family, self.socktype, self.proto,
         self.canonname, self.sockaddr) = info
        return info[:4] + info[4]

    def free(self):
        pass
        

def getaddrinfo(host, port, family, socktype, proto, flags):
    return ADDRINFO(host, port, family, socktype, proto, flags)
