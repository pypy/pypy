"""
An RPython implementation of getnameinfo().
This is a rewrite of the CPython source: Modules/getaddrinfo.c
"""
from pypy.rlib import _rsocket_rffi as _c
from pypy.rlib.rsocket import RSocketError, GAIError
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_uint

NI_NOFQDN = 0x00000001
NI_NUMERICHOST = 0x00000002
NI_NAMEREQD = 0x00000004
NI_NUMERICSERV = 0x00000008
NI_DGRAM = 0x00000010

def _getservicename(sin_port, flags):
    if flags & NI_NUMERICSERV:
        sp = lltype.nullptr(_c.cConfig.servent)
    elif flags & NI_DGRAM:
        sp = _c.getservbyport(sin_port, "udp")
    else:
        sp = _c.getservbyport(sin_port, "tcp")

    if sp:
        serv = rffi.charp2str(sp.c_s_name)
    else:
        serv = "%d" % r_uint(_c.ntohs(sin_port))

    return serv
    

def getnameinfo(address, flags):
    if address.family != _c.AF_INET:
        raise RSocketError("unknown address family")

    sockaddr = address.lock(_c.sockaddr_in)
    try:
        sin_port = sockaddr.c_sin_port
        sin_addr = sockaddr.c_sin_addr

        v4a = rffi.cast(lltype.Unsigned, _c.ntohl(sin_addr.c_s_addr))
        if (v4a & r_uint(0xf0000000) == r_uint(0xe0000000) or # IN_MULTICAST()
            v4a & r_uint(0xe0000000) == r_uint(0xe0000000)):  # IN_EXPERIMENTAL()
            flags |= NI_NUMERICHOST
        # XXX Why does this work in CPython?
        # v4a >>= 24 # = IN_CLASSA_NSHIFT
        # if v4a in (0, 127): # = IN_LOOPBACKNET
        #     flags |= NI_NUMERICHOST
        numsize = _c.INET_ADDRSTRLEN

        serv = _getservicename(sin_port, flags)

        if not (flags & NI_NUMERICHOST):
            p = rffi.cast(rffi.VOIDP, sin_addr)
            hostent = _c.gethostbyaddr(p, rffi.sizeof(_c.in_addr),
                                       sockaddr.c_sin_family)
        else:
            hostent = None

        if hostent:
            from pypy.rlib.rsocket import gethost_common
            host, _, _ = gethost_common("", hostent)
        else:
            host = rffi.charp2str(_c.inet_ntoa(sin_addr))

    finally:
        address.unlock()

    return host, serv

