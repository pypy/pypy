import ctypes_socket as _c


globals().update(_c.constants)


class socket(object):

    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0):
        self.family = family
        self.type   = type
        self.proto  = proto
        self._fd = _c.socket(family, type, proto)
        if self._fd == -1:
            XXX

    def __del__(self):
        if self._fd != -1:
            _c.closesocket(self._fd)

    def close(self):
        fd = self._fd
        if fd != -1:
            self._fd = -1
            _c.closesocket(fd)

    def bind(self, addr):
        caddr, caddrlen = self._getsockaddr(addr)
        res = _c.bind(self._fd, caddr, caddrlen)
        if res < 0:
            XXX

    def _getsockaddr(self, addr):
        if self.family == AF_INET:
            (host, port) = addr
            caddr = sockaddr_in()
            caddr.sin_family = AF_INET
            caddr.sin_port   = port
            caddr.sin_addr.s_addr = getaddrinfo(host)
        else:
            XXX
