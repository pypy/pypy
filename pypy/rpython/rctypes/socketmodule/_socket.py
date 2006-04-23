from ctypes import c_char_p, POINTER, pointer, byref, cast, create_string_buffer, sizeof
import ctypes_socket as _c


globals().update(_c.constants)


class error(Exception):
    pass

def _ip_to_number(ip):
    p1, p2, p3, p4 = [ int(part) for part in ip.split('.') ]
    num = ((p4 * 256 + p3) * 256 + p2) * 256 + p1
    return num


class socket(object):

    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0):
        self.family = family
        self.type   = type
        self.proto  = proto
        self._fd = _c.socket(family, type, proto)
        if self._fd == -1:
            raise error(_c.errno.value)

    def __del__(self):
        if self._fd != -1:
            _c.socketclose(self._fd)

    def close(self):
        fd = self._fd
        if fd != -1:
            self._fd = -1
            _c.closesocket(fd)

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
            caddr.sin_addr.s_addr = _ip_to_number(ip)
            return caddr
        else:
            raise NotImplementedError('sorry') # XXX
    
    def listen(self, backlog):
        if self._fd != -1:
            fd = self._fd
            res = _c.listen(fd, backlog)
            if res == -1:
                XXX
        else:
            XXX
                    
    def accept(self):
        pass

    def connect_ex(self):
        pass
    
    def dup(self):
        pass
    
    def fileno(self):
        pass
    
    def getpeername(self):
        pass
    
    def getsockname(self):
        pass
    
    def getsockopt(self):
        pass
    
    def gettimeout(self):
        pass
    
    def makefile(self):
        pass
    
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
        caddr = self._getsockaddr(addr)
        paddr = cast(pointer(caddr), _c.sockaddr_ptr)
        result = _c.socketconnect(self._fd, paddr, sizeof(caddr))
        if result == -1:
            raise error(_c.errno.value)

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
