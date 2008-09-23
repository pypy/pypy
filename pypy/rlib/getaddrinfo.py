"""
An RPython implementation of getaddrinfo().
This is a rewrite of the CPython source: Modules/getaddrinfo.c
"""

from pypy.rlib import _rsocket_rffi as _c
from pypy.rlib.rsocket import GAIError, CSocketError
from pypy.rlib.rsocket import gethost_common, make_address
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_uint

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
        if not ("0" <= c <= "9"):
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
            port = sp.c_s_port
            if socktype == GAI_ANY:
                s_proto = rffi.charp2str(sp.c_s_proto)
                if s_proto == "udp":
                    socktype = _c.SOCK_DGRAM
                    protocol = _c.IPPROTO_UDP
                elif s_proto == "tcp":
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

            sin = rffi.make(_c.sockaddr_in)
            try:
                rffi.setintfield(sin, 'c_sin_family', _c.AF_INET)
                rffi.setintfield(sin, 'c_sin_port', port)
                if flags & _c.AI_PASSIVE:
                    s_addr = 0x0         # addrany
                else:
                    s_addr = 0x0100007f  # loopback
                rffi.setintfield(sin.c_sin_addr, 'c_s_addr', s_addr)

                addr = make_address(rffi.cast(_c.sockaddr_ptr, sin),
                                    rffi.sizeof(_c.sockaddr_in),
                                    address_to_fill)

                result.append((_c.AF_INET, socktype, protocol, "",  # xxx canonname meaningless? "anyaddr"
                               addr))
            finally:
                lltype.free(sin, flavor='raw')

        if not result:
            raise GAIError(EAI_FAMILY)
        return result

    # hostname as numeric name
    if family in (_c.AF_UNSPEC, _c.AF_INET):

        packedaddr = _c.inet_addr(hostname)
        if packedaddr != rffi.cast(rffi.UINT, INADDR_NONE):

            v4a = rffi.cast(lltype.Unsigned, _c.ntohl(packedaddr))
            if (v4a & r_uint(0xf0000000) == r_uint(0xe0000000) or # IN_MULTICAST()
                v4a & r_uint(0xe0000000) == r_uint(0xe0000000)):  # IN_EXPERIMENTAL()
                flags &= ~_c.AI_CANONNAME
            v4a >>= 24 # = IN_CLASSA_NSHIFT
            if v4a == r_uint(0) or v4a == r_uint(127): # = IN_LOOPBACKNET
                flags &= ~_c.AI_CANONNAME

            sin = rffi.make(_c.sockaddr_in)
            try:
                rffi.setintfield(sin, 'c_sin_family', _c.AF_INET)
                rffi.setintfield(sin, 'c_sin_port', port)
                rffi.setintfield(sin.c_sin_addr, 'c_s_addr', packedaddr)
                addr = make_address(rffi.cast(_c.sockaddr_ptr, sin),
                                    rffi.sizeof(_c.sockaddr_in),
                                    address_to_fill)
            finally:
                lltype.free(sin, flavor='raw')

            if not flags & _c.AI_CANONNAME:
                canonname = ""
            else:
                # getaddrinfo() is a name->address translation function,
                # and it looks strange that we do addr->name translation
                # here.
                # This is what python2.3 did on Windows:
                # if sys.version < (2, 4):
                #     canonname = get_name(hostname, sin.sin_addr,
                #                          sizeof(_c.in_addr))
                canonname = hostname
            return [(_c.AF_INET, socktype, protocol, canonname, addr)]

    if flags & _c.AI_NUMERICHOST:
        raise GAIError(EAI_NONAME)

    # hostname as alphabetical name
    result = get_addr(hostname, socktype, protocol, port, address_to_fill)

    if result:
        return result

    raise GAIError(EAI_FAIL)

##def get_name(hostname, addr, addrlen):
##    hostent = _c.gethostbyaddr(pointer(addr), addrlen, _c.AF_INET)
##
##    # if reverse lookup fail,
##    # return address anyway to pacify calling application.
##    if not hostent:
##        return hostname
##
##    hname, aliases, address_list = gethost_common("", hostent)
##    if hostent and hostent.contents.h_name and hostent.contents.h_addr_list[0]:
##        return hostent.contents.h_name
##    else:
##        return hostname

def get_addr(hostname, socktype, protocol, port, address_to_fill):
    hostent = _c.gethostbyname(hostname)

    if not hostent:
        raise GAIError(EAI_FAIL)

    hname, aliases, address_list = gethost_common("", hostent)
        
    result = []

    for address in address_list:
        if address.family == _c.AF_INET:
            a = address.lock(_c.sockaddr_in)
            rffi.setintfield(a, 'c_sin_port', r_uint(port) & 0xffff)
            address.unlock()
        a = address.lock()
        addr = make_address(a, address.addrlen, address_to_fill)
        address.unlock()
        result.append((address.family,
                       socktype,
                       protocol,
                       "", # XXX canonname?
                       addr))

    return result
