from ctypes import c_char_p, POINTER, pointer, byref, cast, create_string_buffer, sizeof
import ctypes_socket as _c
import os

globals().update(_c.constants)


class error(Exception):
    pass

def makesockaddr(self, caddr):
    family = caddr.sa_family
    if family == AF_INET:
        caddr = cast(pointer(caddr), POINTER(_c.sockaddr_in)).contents
        return (_c.inet_ntoa(caddr.sin_addr), _c.ntohs(caddr.sin_port))
    else:
        raise NotImplementedError('Unsupported address family') # XXX


class socket(object):

    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, _fd=None):
        self.family = family
        self.type   = type
        self.proto  = proto
        if _fd is None:
            self._fd = _c.socket(family, type, proto)
            if self._fd == -1:
                raise error(_c.errno.value)
        else:
            self._fd = _fd
            
    def __del__(self):
        if self._fd != -1:
            _c.socketclose(self._fd)

    def close(self):
        fd = self._fd
        if fd != -1:
            self._fd = -1
            _c.socketclose(fd)

    def bind(self, addr):
        caddr, caddrlen = self._getsockaddr(addr)
        res = _c.bind(self._fd, caddr, caddrlen)
        if res < 0:
            raise error(_c.errno.value)

    def _getsockaddr(self, addr):
        if self.family == AF_INET:
            (host, port) = addr
            ip = host # XXX
            caddr = _c.sockaddr_in()
            caddr.sin_family = AF_INET
            caddr.sin_port = _c.htons(port)
            _c.inet_aton(ip, pointer(caddr.sin_addr))
            return caddr
        else:
            raise NotImplementedError('Unsupported address family') # XXX

    def listen(self, backlog):
        if self._fd != -1:
            fd = self._fd
            res = _c.listen(fd, backlog)
            if res == -1:
                raise error(_c.errno.value)
        else:
            XXX
                    
    def accept(self):
        peeraddr = _c.sockaddr()
        peeraddrlen = _c.socklen_t(sizeof(peeraddr))
        newfd = _c.socketaccept(self._fd, pointer(peeraddr),
                                pointer(peeraddrlen))
        if newfd < 0:
            raise error(_c.errno.value)
        newsocket = socket(self.family, self.type, self.proto, newfd)
        return (newsocket, makesockaddr(peeraddr))
    
    def connect_ex(self, addr):
        caddr = self._getsockaddr(addr)
        paddr = cast(pointer(caddr), _c.sockaddr_ptr)
        result = _c.socketconnect(self._fd, paddr,
                                  _c.socklen_t(sizeof(caddr)))
        if result == -1:
            return _c.errno.value
        return 0
    
    def dup(self):
        raise NotImplementedError
    
    def fileno(self):
        return self._fd
    
    def getpeername(self):
        peeraddr = _c.sockaddr()
        peeraddrlen = _c.socklen_t(sizeof(peeraddr))
        res = _c.socketgetpeername(self._fd, pointer(peeraddr),
                                   pointer(peeraddrlen))
        if res < 0:
            raise error(_c.errno.value)
        return makesockaddr(peeraddr)
    
    def getsockname(self):
        peeraddr = _c.sockaddr()
        peeraddrlen = _c.socklen_t(sizeof(peeraddr))
        res = _c.socketgetsockname(self._fd, pointer(peeraddr),
                                   pointer(peeraddrlen))
        if res < 0:
            raise error(_c.errno.value)
        return makesockaddr(peeraddr)
    
    def getsockopt(self, level, optname, buflen=-1):
        pass
    
    def gettimeout(self):
        pass
    
    def makefile(self):
        raise NotImplementedError
    
    def recv(self):
        pass
    
    def recvfrom(self):
        pass
    
    def send(self):
        pass
    
    def sendall(self):
        pass
    
    def sendto(self):
        pass
    
    def setblocking(self):
        pass
    
    def setsockopt(self):
        pass
        
    def settimeout(self):
        pass
    
    def shutdown(self):
        pass

    def connect(self, addr):
        err = self.connect_ex(addr)
        if err:
            raise error(err)
        
def makeipaddr(caddr, caddrlen):
    buf = create_string_buffer(NI_MAXHOST)
    error = _c.getnameinfo(caddr, caddrlen, buf, NI_MAXHOST,
                           c_char_p(), 0, NI_NUMERICHOST)
    if error:
        XXX
    return buf.value

def makesockaddr(caddr, caddrlen, proto):
    if caddrlen == 0:
        # No address -- may be recvfrom() from known socket
        return None
    if caddr.contents.sa_family == AF_INET:
        a = cast(caddr, POINTER(_c.sockaddr_in))
        return makeipaddr(caddr, caddrlen), _c.ntohs(a.contents.sin_port)
    else:
        XXX

def getaddrinfo(host, port, family=AF_UNSPEC, socktype=0, proto=0, flags=0):
    if isinstance(port, (int, long)):
        port = str(port)
    hptr = c_char_p(host)   # string or None
    pptr = c_char_p(port)   # int or string or None
    hints = _c.addrinfo()
    hints.ai_family = family
    hints.ai_socktype = socktype
    hints.ai_protocol = proto
    hints.ai_flags = flags
    res0 = POINTER(_c.addrinfo)()
    error = _c.getaddrinfo(hptr, pptr, byref(hints), byref(res0))
    if error:
        XXX
    try:
        return _getaddrinfo_chainedlist(res0, proto)
    finally:
        if res0:
            _c.freeaddrinfo(res0)

def _getaddrinfo_chainedlist(res, proto):
    result = []
    while res:
        res = res.contents
        addr = makesockaddr(res.ai_addr, res.ai_addrlen, proto)
        result.append((res.ai_family, res.ai_socktype, res.ai_protocol,
                       res.ai_canonname or "", addr))
        res = res.ai_next
    return result
