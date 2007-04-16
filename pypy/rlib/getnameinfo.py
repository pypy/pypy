"""
An RPython implementation of getnameinfo() based on ctypes.
This is a rewrite of the CPython source: Modules/getaddrinfo.c
"""
from ctypes import POINTER, sizeof, cast, pointer
from pypy.rlib import _rsocket_ctypes as _c
from pypy.rlib.rsocket import RSocketError, GAIError

NI_NOFQDN = 0x00000001
NI_NUMERICHOST = 0x00000002
NI_NAMEREQD = 0x00000004
NI_NUMERICSERV = 0x00000008
NI_DGRAM = 0x00000010

def _getservicename(sin_port, flags):
    if flags & NI_NUMERICSERV:
        sp = None
    elif flags & NI_DGRAM:
        sp = _c.getservbyport(sin_port, "udp")
    else:
        sp = _c.getservbyport(sin_port, "tcp")

    if sp:
        serv = sp.contents.s_name
    else:
        serv = "%d" % _c.ntohs(sin_port)

    return serv
    

def getnameinfo(_addr, flags):
    addr = _addr.addr

    if addr.sa_family != _c.AF_INET:
        raise RSocketError("unknown address family")

    sockaddr = cast(pointer(addr), POINTER(_c.sockaddr_in)).contents
    sin_port = sockaddr.sin_port
    sin_addr = sockaddr.sin_addr

    v4a = _c.ntohl(sin_addr.s_addr)
    if (v4a & 0xf0000000 == 0xe0000000 or # IN_MULTICAST()
        v4a & 0xe0000000 == 0xe0000000):  # IN_EXPERIMENTAL()
        flags |= NI_NUMERICHOST
    # XXX Why does this work in CPython?
    # v4a >>= 24 # = IN_CLASSA_NSHIFT
    # if v4a in (0, 127): # = IN_LOOPBACKNET
    #     flags |= NI_NUMERICHOST
    numsize = _c.INET_ADDRSTRLEN

    serv = _getservicename(sin_port, flags)

    if not (flags & NI_NUMERICHOST):
        hostent = _c.gethostbyaddr(pointer(sin_addr), sizeof(_c.in_addr), addr.sa_family)
    else:
        hostent = None

    if hostent:
        from pypy.rlib.rsocket import gethost_common
        host, _, _ = gethost_common("", hostent)
    else:
        from pypy.rlib.rsocket import copy_buffer
        host = _c.inet_ntoa(sin_addr)
        #buf = copy_buffer(ptr, len(ptr))
        #host = buf.raw
        
    return host, serv

