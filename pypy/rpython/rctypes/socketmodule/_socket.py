from ctypes import c_char_p, POINTER, pointer, byref, cast, create_string_buffer, sizeof
import ctypes_socket as _c
import os

globals().update(_c.constants)


class error(Exception):
    def __init__(self, errno):
        Exception.__init__(self, errno, _c.strerror(errno)) 


class socket(object):

    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, _fd=None):
        self.family = family
        self.type   = type
        self.proto  = proto
        if _fd is None:
            self._fd = _c.socket(family, type, proto)
            if self._fd == -1:
                raise error(_c.geterrno())
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
        caddr = self._getsockaddr(addr)
        paddr = cast(pointer(caddr), _c.sockaddr_ptr)
        res = _c.socketbind(self._fd, paddr, sizeof(caddr))
        if res < 0:
            raise error(_c.geterrno())

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
        fd = self._fd
        if backlog < 1:
            backlog = 1
        res = _c.socketlisten(fd, backlog)
        if res == -1:
            raise error(_c.geterrno())
                    
    def accept(self):
        peeraddr = pointer(_c.sockaddr())
        peeraddrlen = _c.socklen_t(sizeof(_c.sockaddr))
        newfd = _c.socketaccept(self._fd, peeraddr,
                                pointer(peeraddrlen))
        if newfd < 0:
            raise error(_c.geterrno())
        newsocket = socket(self.family, self.type, self.proto, newfd)
        return (newsocket, makesockaddr(peeraddr, peeraddrlen, self.proto))
    
    def connect_ex(self, addr):
        caddr = self._getsockaddr(addr)
        paddr = cast(pointer(caddr), _c.sockaddr_ptr)
        result = _c.socketconnect(self._fd, paddr,
                                  _c.socklen_t(sizeof(caddr)))
        if result == -1:
            return _c.geterrno()
        return 0
    
    def dup(self):
        raise NotImplementedError
    
    def fileno(self):
        return self._fd
    
    def getpeername(self):
        peeraddr = pointer(_c.sockaddr())
        peeraddrlen = _c.socklen_t(sizeof(_c.sockaddr))
        res = _c.socketgetpeername(self._fd, peeraddr,
                                   pointer(peeraddrlen))
        if res < 0:
            raise error(_c.geterrno())
        return makesockaddr(peeraddr, peeraddrlen, self.proto)
    
    def getsockname(self):
        peeraddr = pointer(_c.sockaddr())
        peeraddrlen = _c.socklen_t(sizeof(_c.sockaddr))
        res = _c.socketgetsockname(self._fd, peeraddr,
                                   pointer(peeraddrlen))
        if res < 0:
            raise error(_c.geterrno())
        return makesockaddr(peeraddr, peeraddrlen, self.proto)
    
    def getsockopt(self, level, optname, buflen=-1):
        pass
    
    def gettimeout(self):
        pass
    
    def makefile(self):
        raise NotImplementedError
    
    def recv(self, bufsize, flags=0):
        buf = create_string_buffer(bufsize)
        read_bytes = _c.socketrecv(self._fd, buf, bufsize, flags)
        if read_bytes < 0:
            raise error(_c.errno)
        return buf[:read_bytes]
    
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
        
SocketType = socket

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
        raise NotImplementedError("Unsupported address family %d" % caddr.contents.sa_family)

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
