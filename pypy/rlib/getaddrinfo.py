"""
An RPython implementation of getaddrinfo() based on ctypes.
This is a rewrite of the CPython source: Modules/getaddrinfo.c
"""

from ctypes import POINTER, sizeof, cast, pointer
from pypy.rlib import _rsocket_ctypes as _c
from pypy.rlib.rsocket import GAIError, CSocketError
from pypy.rlib.rsocket import gethost_common, make_address

# valid flags for addrinfo
AI_MASK = (_c.AI_PASSIVE | _c.AI_CANONNAME | _c.AI_NUMERICHOST)

GAI_ERRORS = [
    (1, 'EAI_ADDRFAMILY', "address family for hostname not supported"),
    (2, 'EAI_AGAIN', "temporary failure in name resolution"),
    (3, 'EAI_BADFLAGS', "invalid value for ai_flags"),
    (4, 'EAI_FAIL', "failure in name resolution"),
    (5, 'EAI_FAMILY', "ai_family not supported"),
    (6, 'EAI_MEMORY', "memory allocation failure"),
    (7, 'EAI_NODATA', "no address associated with hostname"),
    (8, 'EAI_NONAME', "hostname nor servname provided, or not known"),
    (9, 'EAI_SERVICE', "servname not supported for ai_socktype"),
    (10, 'EAI_SOCKTYPE', "ai_socktype not supported"),
    (11, 'EAI_SYSTEM', "system error returned in errno"),
    (12, 'EAI_BADHINTS', "invalid value for hints"),
    (13, 'EAI_PROTOCOL', "resolved protocol is unknown."),
    (14, 'EAI_MAX', "unknown error"),
]

GAI_ERROR_MESSAGES = {}

for value, name, text in GAI_ERRORS:
    globals()[name] = value
    GAI_ERROR_MESSAGES[value] = text

# Replacement function for rsocket.GAIError.get_msg
def GAIError_getmsg(self):
    return GAI_ERROR_MESSAGES[self.errno]

# str.isdigit is not RPython, so provide our own
def str_isdigit(name):
    if name == "":
        return False
    for c in name:
        if c not in "012345789":
            return False
    return True

GAI_ANY = 0
INADDR_NONE = 0xFFFFFFFF

def getaddrinfo(hostname, servname,
                family=_c.AF_UNSPEC, socktype=0,
                protocol=0, flags=0,
                address_to_fill=None):

    if not hostname and not servname:
        raise GAIError(EAI_NONAME)

    # error checks for hints
    if flags & ~AI_MASK:
        raise GAIError(EAI_BADFLAGS)
    if family not in (_c.AF_UNSPEC, _c.AF_INET):
        raise GAIError(EAI_FAMILY)

    if socktype == GAI_ANY:
        if protocol == GAI_ANY:
            pass
        elif protocol == _c.IPPROTO_UDP:
            socktype = _c.SOCK_DGRAM
        elif protocol == _c.IPPROTO_TCP:
            socktype = _c.SOCK_STREAM
        else:
            socktype = _c.SOCK_RAW

    elif socktype == _c.SOCK_RAW:
        pass
    elif socktype == _c.SOCK_DGRAM:
        if protocol not in (_c.IPPROTO_UDP, GAI_ANY):
            raise GAIError(EAI_BADHINTS)
        protocol = _c.IPPROTO_UDP
    elif socktype == _c.SOCK_STREAM:
        if protocol not in (_c.IPPROTO_TCP, GAI_ANY):
            raise GAIError(EAI_BADHINTS)
        protocol = _c.IPPROTO_TCP
    else:
        raise GAIError(EAI_SOCKTYPE)

    port = GAI_ANY

    # service port
    if servname:
        if str_isdigit(servname):
            port = _c.htons(int(servname))
            # On windows, python2.3 uses getattrinfo.c,
            # python2.4 uses VC2003 implementation of getaddrinfo().
            # if sys.version < (2, 4)
            #     socktype = _c.SOCK_DGRAM
            #     protocol = _c.IPPROTO_UDP
        else:
            if socktype == _c.SOCK_DGRAM:
                proto = "udp"
            elif socktype == _c.SOCK_STREAM:
                proto = "tcp"
            else:
                proto = None

            sp = _c.getservbyname(servname, proto)
            if not sp:
                raise GAIError(EAI_SERVICE)
            port = sp.contents.s_port
            if socktype == GAI_ANY:
                if sp.contents.s_proto == "udp":
                    socktype = _c.SOCK_DGRAM
                    protocol = _c.IPPROTO_UDP
                elif sp.contents.s_proto == "tcp":
                    socktype = _c.SOCK_STREAM
                    protocol = _c.IPPROTO_TCP
                else:
                    raise GAIError(EAI_PROTOCOL)

    # hostname == NULL
    # passive socket -> anyaddr (0.0.0.0 or ::)
    # non-passive socket -> localhost (127.0.0.1 or ::1)
    if not hostname:
        result = []
        if family in (_c.AF_UNSPEC, _c.AF_INET):

            sin = _c.sockaddr_in(sin_family=_c.AF_INET, sin_port=port)
            if flags & _c.AI_PASSIVE:
                sin.sin_addr.s_addr = 0x0        # addrany
            else:
                sin.sin_addr.s_addr = 0x0100007f # loopback

            addr = make_address(cast(pointer(sin), POINTER(_c.sockaddr)),
                                sizeof(_c.sockaddr_in), address_to_fill)

            result.append((_c.AF_INET, socktype, protocol, "",  # xxx canonname meaningless? "anyaddr"
                           addr))

        if not result:
            raise GAIError(EAI_FAMILY)
        return result

    # hostname as numeric name
    if family in (_c.AF_UNSPEC, _c.AF_INET):

        packedaddr = _c.inet_addr(hostname)
        if packedaddr != INADDR_NONE:

            v4a = _c.ntohl(packedaddr)
            if (v4a & 0xf0000000 == 0xe0000000 or # IN_MULTICAST()
                v4a & 0xe0000000 == 0xe0000000):  # IN_EXPERIMENTAL()
                flags &= ~_c.AI_CANONNAME
            v4a >>= 24 # = IN_CLASSA_NSHIFT
            if v4a in (0, 127): # = IN_LOOPBACKNET
                flags &= ~_c.AI_CANONNAME

            if not flags & _c.AI_CANONNAME:
                sin = _c.sockaddr_in(sin_family=_c.AF_INET, sin_port=port)
                sin.sin_addr.s_addr = packedaddr
                addr = make_address(cast(pointer(sin), POINTER(_c.sockaddr)),
                                    sizeof(_c.sockaddr_in), address_to_fill)
                return [(_c.AF_INET, socktype, protocol, None, addr)]
            else:
                sin = _c.sockaddr_in(sin_family=_c.AF_INET, sin_port=port)

                sin.sin_addr.s_addr = packedaddr

                # getaddrinfo() is a name->address translation function,
                # and it looks strange that we do addr->name translation here.
                # This is what python2.3 did on Windows:
                # if sys.version < (2, 4):
                #     canonname = get_name(hostname, sin.sin_addr,
                #                          sizeof(_c.in_addr))
                canonname = hostname

                addr = make_address(cast(pointer(sin), POINTER(_c.sockaddr)),
                                    sizeof(_c.sockaddr_in), address_to_fill)
                return [(_c.AF_INET, socktype, protocol, canonname, addr)]

    if flags & _c.AI_NUMERICHOST:
        raise GAIError(EAI_NONAME)

    # hostname as alphabetical name
    result = get_addr(hostname, socktype, protocol, port, address_to_fill)

    if result:
        return result

    raise GAIError(EAI_FAIL)

def get_name(hostname, addr, addrlen):
    hostent = _c.gethostbyaddr(pointer(addr), addrlen, _c.AF_INET)

    # if reverse lookup fail,
    # return address anyway to pacify calling application.
    if not hostent:
        return hostname

    hname, aliases, address_list = gethost_common("", hostent)
    if hostent and hostent.contents.h_name and hostent.contents.h_addr_list[0]:
        return hostent.contents.h_name
    else:
        return hostname

def get_addr(hostname, socktype, protocol, port, address_to_fill):
    hostent = _c.gethostbyname(hostname)

    if not hostent:
        raise GAIError(EAI_FAIL)

    hname, aliases, address_list = gethost_common("", hostent)
        
    result = []

    for address in address_list:
        if address.addr.sa_family == _c.AF_INET:
            a = cast(pointer(address.addr), POINTER(_c.sockaddr_in)).contents
            a.sin_port = port & 0xffff
        addr = make_address(pointer(address.addr),address.addrlen,address_to_fill)
        result.append((address.addr.sa_family,
                       socktype,
                       protocol,
                       "", # XXX canonname?
                       addr))

    return result
