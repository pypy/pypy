import _socket

from pypy.rpython.rstr import STR
from pypy.rpython.lltypesystem.lltype import GcStruct, Signed, Array, Char, Ptr, malloc
from pypy.rpython.module.support import to_rstr, from_rstr
from pypy.rpython.module.support import to_opaque_object, from_opaque_object
from pypy.module._socket.rpython import rsocket

def ll__socket_gethostname():
    return to_rstr(_socket.gethostname())
ll__socket_gethostname.suggested_primitive = True

def ll__socket_gethostbyname(name):
    return to_rstr(_socket.gethostbyname(name))
ll__socket_gethostbyname.suggested_primitive = True

def ll__socket_getaddrinfo(host, port, family, socktype, proto, flags):
    addr = rsocket.getaddrinfo(from_rstr(host), port,
                               family, socktype, proto, flags)
    return to_opaque_object(addr)
ll__socket_getaddrinfo.suggested_primitive = True


# XXX The tag and the items names must have the same name as
# the structure computed from ann_addrinfo
ADDRINFO_RESULT = GcStruct('tuple8',
                           ('item0', Signed),
                           ('item1', Signed),
                           ('item2', Signed),
                           ('item3', Ptr(STR)),
                           ('item4', Ptr(STR)),
                           ('item5', Signed),
                           ('item6', Signed),
                           ('item7', Signed),
                           )

def ll__socket_addrinfo(family, socktype, proto, canonname,
                        ipaddr, port, flowinfo, scopeid):
    tup = malloc(ADDRINFO_RESULT)
    tup.item0 = family
    tup.item1 = socktype
    tup.item2 = proto
    tup.item3 = canonname
    tup.item4 = ipaddr
    tup.item5 = port
    tup.item6 = flowinfo  # ipV6
    tup.item7 = scopeid   # ipV6
    return tup

def ll__socket_nextaddrinfo(opaqueaddr):
    addr = from_opaque_object(opaqueaddr)
    return addr.nextinfo()
ll__socket_nextaddrinfo.suggested_primitive = True

def ll__socket_freeaddrinfo(opaqueaddr):
    addr = from_opaque_object(opaqueaddr)
    return addr.free()
ll__socket_freeaddrinfo.suggested_primitive = True

def ll__socket_ntohs(htons):
    return _socket.ntohs(htons)
ll__socket_ntohs.suggested_primitive = True

def ll__socket_htons(ntohs):
    return _socket.ntohs(htons)
ll__socket_htons.suggested_primitive = True

def ll__socket_htonl(ntohl):
    return _socket.htonl(ntohl)
ll__socket_htonl.suggested_primitive = True

def ll__socket_ntohl(htonl):
    return _socket.ntohl(htonl)
ll__socket_ntohl.suggested_primitive = True

def ll__socket_newsocket(family, type, protocol):
#    from pypy.module._socket.rpython import rsocket
#    return rsocket.newsocket(family, type, protocol).fileno()
    return 0
ll__socket_newsocket.suggested_primitive = True

