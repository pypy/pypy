import os
import distutils
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool import util      # ctypes.util from 0.9.9.6
from pypy.rpython.rctypes.aerrno import geterrno
from ctypes import *

includes = ('sys/types.h',
            'sys/socket.h',
            'netinet/in.h',
            'netinet/tcp.h',
            'unistd.h',
            'fcntl.h',
            'stdio.h',
            'netdb.h',
            'arpa/inet.h',
            'stdint.h', 
            )
HEADER = ''.join(['#include <%s>\n' % filename for filename in includes])
constants = {}

class CConfig:
    _header_ = HEADER
    # constants
    O_NONBLOCK = ctypes_platform.ConstantInteger('O_NONBLOCK')
    F_GETFL = ctypes_platform.ConstantInteger('F_GETFL')
    F_SETFL = ctypes_platform.ConstantInteger('F_SETFL')
    
constant_names = ['AF_APPLETALK', 'AF_ASH', 'AF_ATMPVC', 'AF_ATMSVC', 'AF_AX25',
                  'AF_BLUETOOTH', 'AF_BRIDGE', 'AF_ECONET', 'AF_INET', 'AF_INET6',
                  'AF_IPX', 'AF_IRDA', 'AF_KEY', 'AF_NETBEUI', 'AF_NETLINK',
                  'AF_NETROM', 'AF_PACKET', 'AF_PPPOX', 'AF_ROSE', 'AF_ROUTE',
                  'AF_SECURITY', 'AF_WANPIPE', 'AF_SNA', 'AF_UNIX', 'AF_X25',
                  'AF_UNSPEC', 'AI_ADDRCONFIG', 'AI_ALL', 'AI_CANONNAME',
                  'AI_DEFAULT', 'AI_MASK', 'AI_NUMERICHOST', 'AI_NUMERICSERV', 'AI_PASSIVE', 'AI_V4MAPPED',
                  'AI_V4MAPPED_CFG', 'BDADDR_ANY', 'EAI_ADDRFAMILY', 'EAI_AGAIN', 'EAI_BADFLAGS',
                  'EAI_BADHINTS', 'EAI_FAIL', 'EAI_FAMILY', 'EAI_MAX', 'EAI_MEMORY',
                  'EAI_NODATA', 'EAI_NONAME', 'EAI_PROTOCOL', 'EAI_SERVICE', 'EAI_SOCKTYPE',
                  'EAI_SYSTEM', 'INADDR_UNSPEC_GROUP', 'IPPROTO_AH',
                  'IPPROTO_DSTOPTS', 'IPPROTO_EGP', 'IPPROTO_EON', 'IPPROTO_ESP',
                  'IPPROTO_FRAGMENT', 'IPPROTO_GGP', 'IPPROTO_GRE', 'IPPROTO_HELLO',
                  'IPPROTO_HOPOPTS', 'IPPROTO_ICMP', 'IPPROTO_ICMPV6', 'IPPROTO_IDP',
                  'IPPROTO_IGMP', 'IPPROTO_IPCOMP', 'IPPROTO_IPIP',
                  'IPPROTO_IPV4', 'IPPROTO_IPV6', 'IPPROTO_MAX', 'IPPROTO_ND', 'IPPROTO_NONE',
                  'IPPROTO_PIM', 'IPPROTO_PUP', 'IPPROTO_ROUTING',
                  'IPPROTO_RSVP', 'IPPROTO_TCP', 'IPPROTO_TP', 'IPPROTO_XTP',
                  'IPV6_CHECKSUM', 'IPV6_DSTOPTS', 'IPV6_HOPLIMIT', 'IPV6_HOPOPTS',
                  'IPV6_JOIN_GROUP', 'IPV6_LEAVE_GROUP', 'IPV6_MULTICAST_HOPS',
                  'IPV6_MULTICAST_IF', 'IPV6_MULTICAST_LOOP', 'IPV6_NEXTHOP', 'IPV6_PKTINFO',
                  'IPV6_RTHDR', 'IPV6_RTHDR_TYPE_0', 'IPV6_UNICAST_HOPS', 'IPV6_V6ONLY',
                  'IP_ADD_MEMBERSHIP', 'IP_DEFAULT_MULTICAST_LOOP', 'IP_DEFAULT_MULTICAST_TTL',
                  'IP_DROP_MEMBERSHIP', 'IP_HDRINCL', 'IP_MAX_MEMBERSHIPS', 'IP_MULTICAST_IF',
                  'IP_MULTICAST_LOOP', 'IP_MULTICAST_TTL', 'IP_OPTIONS', 'IP_RECVDSTADDR',
                  'IP_RECVOPTS', 'IP_RECVRETOPTS', 'IP_RETOPTS', 'IP_TOS', 'IP_TTL',
                  'MSG_CTRUNC', 'MSG_DONTROUTE', 'MSG_DONTWAIT', 'MSG_EOR', 'MSG_OOB',
                  'MSG_PEEK', 'MSG_TRUNC', 'MSG_WAITALL', 'NI_DGRAM', 'NI_MAXHOST',
                  'NI_MAXSERV', 'NI_NAMEREQD', 'NI_NOFQDN', 'NI_NUMERICHOST', 'NI_NUMERICSERV',
                  'SOCK_DGRAM', 'SOCK_RAW', 'SOCK_RDM',
                  'SOCK_SEQPACKET', 'SOCK_STREAM',  'SOL_SOCKET',
                  'SO_ACCEPTCONN', 'SO_BROADCAST', 'SO_DEBUG', 'SO_DONTROUTE',
                  'SO_ERROR', 'SO_KEEPALIVE', 'SO_LINGER', 'SO_OOBINLINE', 'SO_RCVBUF',
                  'SO_RCVLOWAT', 'SO_RCVTIMEO', 'SO_REUSEADDR', 'SO_REUSEPORT', 'SO_SNDBUF',
                  'SO_SNDLOWAT', 'SO_SNDTIMEO', 'SO_TYPE', 'SO_USELOOPBACK', 'TCP_MAXSEG',
                  'TCP_NODELAY', 'AF_DECnet']
for name in constant_names:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
    
constants["BDADDR_ANY"] =  "00:00:00:00:00:00"
constants["BDADDR_LOCAL"] = "00:00:00:FF:FF:FF"

constants_w_defaults = [('SOL_IP', 0),
                        ('SOL_TCP', 6),
                        ('SOL_UDP', 17),
                        ('SOMAXCONN', 5),
                        ('IPPROTO_IP', 6),
                        ('IPPROTO_UDP', 17),
                        ('IPPROTO_RAW', 255),
                        ('IPPORT_RESERVED', 1024),
                        ('IPPORT_USERRESERVED', 5000),
                        ('INADDR_ANY', 0x00000000),
                        ('INADDR_BROADCAST', 0xffffffff),
                        ('INADDR_LOOPBACK', 0x7F000001),
                        ('INADDR_UNSPEC_GROUP', 0xe0000000),
                        ('INADDR_ALLHOSTS_GROUP', 0xe0000001),
                        ('INADDR_MAX_LOCAL_GROUP', 0xe00000ff),
                        ('INADDR_NONE', 0xffffffff),
                        ('SHUT_RD', 0),
                        ('SHUT_WR', 1),
                        ('SHUT_RDWR', 2)]
for name, default in constants_w_defaults:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
    
# types
CConfig.uint16_t = ctypes_platform.SimpleType('uint16_t', c_ushort)
CConfig.uint32_t = ctypes_platform.SimpleType('uint32_t', c_uint)
CConfig.size_t = ctypes_platform.SimpleType('size_t', c_int)
CConfig.ssize_t = ctypes_platform.SimpleType('ssize_t', c_int)
CConfig.socklen_t = ctypes_platform.SimpleType('socklen_t', c_int)

# struct types
CConfig.sockaddr = ctypes_platform.Struct('struct sockaddr',
                                             [('sa_family', c_int),
                                              ])
sockaddr_ptr = POINTER('sockaddr')
CConfig.in_addr = ctypes_platform.Struct('struct in_addr',
                                         [('s_addr', c_uint)])
CConfig.sockaddr_in = ctypes_platform.Struct('struct sockaddr_in',
                                        [('sin_family', c_int),
                                         ('sin_port',   c_ushort),
                                         ('sin_addr',   CConfig.in_addr)])

CConfig.sockaddr_in6  = ctypes_platform.Struct('struct sockaddr_in6',
                                               [('sin6_flowinfo', c_int),
                                                ('sin6_scope_id', c_int),
                                                ])
addrinfo_ptr = POINTER("addrinfo")
CConfig.addrinfo = ctypes_platform.Struct('struct addrinfo',
                                     [('ai_flags', c_int),
                                      ('ai_family', c_int),
                                      ('ai_socktype', c_int),
                                      ('ai_protocol', c_int),
                                      ('ai_addrlen', c_int),
                                      ('ai_addr', sockaddr_ptr),
                                      ('ai_canonname', c_char_p),
                                      ('ai_next', addrinfo_ptr)])

CConfig.hostent = ctypes_platform.Struct('struct hostent',
                                     [('h_name', c_char_p),
                                      ('h_aliases', POINTER(c_char_p)),
                                      ('h_addrtype', c_int),
                                      ('h_length', c_int),
                                      ('h_addr_list', POINTER(c_char_p))
                                      ])


CConfig.servent = ctypes_platform.Struct('struct servent',
                                         [('s_name', c_char_p),
                                          ('s_port', c_int)])

CConfig.protoent = ctypes_platform.Struct('struct protoent',
                                          [('p_proto', c_int),
                                           ])

class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))

for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value
for name, default in constants_w_defaults:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value
    else:
        constants[name] = default

constants['has_ipv6'] = True # This is a configuration option in CPython

locals().update(constants)

O_NONBLOCK = cConfig.O_NONBLOCK
F_GETFL = cConfig.F_GETFL
F_SETFL = cConfig.F_SETFL

uint16_t = cConfig.uint16_t
uint32_t = cConfig.uint32_t
size_t = cConfig.size_t
ssize_t = cConfig.ssize_t
socklen_t = cConfig.socklen_t
sockaddr = cConfig.sockaddr
sockaddr_size = sizeof(sockaddr)
sockaddr_in = cConfig.sockaddr_in
sockaddr_in6 = cConfig.sockaddr_in6
in_addr = cConfig.in_addr
in_addr_size = sizeof(in_addr)
addrinfo = cConfig.addrinfo

c_int_size = sizeof(c_int)
SetPointerType(addrinfo_ptr, addrinfo)
SetPointerType(sockaddr_ptr, sockaddr)

# functions
dllname = util.find_library('c')
assert dllname is not None
socketdll = cdll.LoadLibrary(dllname)

dup = socketdll.dup
dup.argtypes = [c_int]
dup.restype = c_int

#errno = c_int.in_dll(socketdll, 'errno')

strerror = socketdll.strerror
strerror.argtypes = [c_int]
strerror.restype = c_char_p

gai_strerror = socketdll.gai_strerror
gai_strerror.argtypes = [c_int]
gai_strerror.restype = c_char_p

#h_errno = c_int.in_dll(socketdll, 'h_errno')
#
#hstrerror = socketdll.hstrerror
#hstrerror.argtypes = [c_int]
#hstrerror.restype = c_char_p

socket = socketdll.socket
socket.argtypes = [c_int, c_int, c_int]
socket.restype = c_int

socketclose = os.close

socketconnect = socketdll.connect
socketconnect.argtypes = [c_int, sockaddr_ptr, socklen_t]
socketconnect.restype = c_int

getaddrinfo = socketdll.getaddrinfo
getaddrinfo.argtypes = [c_char_p, c_char_p, addrinfo_ptr,
                        POINTER(addrinfo_ptr)]
getaddrinfo.restype = c_int

freeaddrinfo = socketdll.freeaddrinfo
freeaddrinfo.argtypes = [addrinfo_ptr]
freeaddrinfo.restype = None

getnameinfo = socketdll.getnameinfo
getnameinfo.argtypes = [sockaddr_ptr, socklen_t,
                        c_char_p, size_t,
                        c_char_p, size_t, c_int]
getnameinfo.restype = c_int

htonl = socketdll.htonl
htonl.argtypes = [uint32_t]
htonl.restype = uint32_t

htons = socketdll.htons
htons.argtypes = [uint16_t]
htons.restype = uint16_t

ntohl = socketdll.ntohl
ntohl.argtypes = [uint32_t]
ntohl.restype = uint32_t

ntohs = socketdll.ntohs
ntohs.argtypes = [uint16_t]
ntohs.restype = uint16_t

inet_aton = socketdll.inet_aton
inet_aton.argtypes = [c_char_p, POINTER(in_addr)]
inet_aton.restype = c_int

inet_ntoa = socketdll.inet_ntoa
inet_ntoa.argtypes = [in_addr]
inet_ntoa.restype = c_char_p

close = socketdll.close
close.argtypes = [c_int]
close.restype = c_int

socketaccept = socketdll.accept
socketaccept.argtypes = [c_int, sockaddr_ptr, POINTER(socklen_t)]
socketaccept.restype = c_int

socketbind = socketdll.bind
socketbind.argtypes = [c_int, sockaddr_ptr, socklen_t]
socketbind.restype = c_int

socketlisten = socketdll.listen
socketlisten.argtypes = [c_int, c_int]
socketlisten.restype = c_int

socketgetpeername = socketdll.getpeername
socketgetpeername.argtypes = [c_int, sockaddr_ptr, POINTER(socklen_t)]
socketgetpeername.restype = c_int

socketgetsockname = socketdll.getsockname
socketgetsockname.argtypes = [c_int, sockaddr_ptr, POINTER(socklen_t)]
socketgetsockname.restype = c_int

socketgetsockopt = socketdll.getsockopt
socketgetsockopt.argtypes = [c_int, c_int, c_int, 
                             c_void_p, POINTER(socklen_t)]
socketgetsockopt.restype = c_int

socketsetsockopt = socketdll.setsockopt
socketsetsockopt.argtypes = [c_int, c_int, c_int,
                             c_void_p, #this should be constant
                             socklen_t]
socketsetsockopt.restype = c_int

socketrecv = socketdll.recv
socketrecv.argtypes = [c_int, c_void_p, c_int, c_int]
socketrecv.recv = ssize_t

recvfrom = socketdll.recvfrom
recvfrom.argtypes = [c_int, c_void_p, size_t,
                     c_int, sockaddr_ptr, POINTER(socklen_t)]
recvfrom.restype = ssize_t

send = socketdll.send
send.argtypes = [c_int,
                       c_void_p, #this should be constant
                       size_t, c_int]
send.restype = ssize_t

sendto = socketdll.sendto
sendto.argtypes = [c_int, c_void_p, #this should be constant
                         size_t, c_int, sockaddr_ptr, #this should be const
                         socklen_t]
sendto.restype = ssize_t

socketshutdown = socketdll.shutdown
socketshutdown.argtypes = [c_int, c_int]
socketshutdown.restype = c_int


getaddrinfo = socketdll.getaddrinfo
getaddrinfo.argtypes = [ c_char_p, c_char_p, addrinfo_ptr, POINTER(addrinfo_ptr)]
getaddrinfo.restype = c_int

gethostname = socketdll.gethostname
gethostname.argtypes = [c_char_p, c_int]
gethostname.restype = c_int

gethostbyname = socketdll.gethostbyname
gethostbyname.argtypes = [c_char_p]
gethostbyname.restype = POINTER(cConfig.hostent)

gethostbyaddr = socketdll.gethostbyaddr
gethostbyaddr.argtypes = [c_char_p, c_int, c_int]
gethostbyaddr.restype = POINTER(cConfig.hostent)

getservbyname = socketdll.getservbyname
getservbyname.argtypes = [c_char_p, c_char_p]
getservbyname.restype = POINTER(cConfig.servent)

getservbyport = socketdll.getservbyport
getservbyport.argtypes = [c_int, c_char_p]
getservbyport.restype = POINTER(cConfig.servent)

getprotobyname = socketdll.getprotobyname
getprotobyname.argtypes = [c_char_p]
getprotobyname.restype = POINTER(cConfig.protoent)

fcntl = socketdll.fcntl
fcntl.argtypes = [c_int] * 3
fcntl.restype = c_int

memcpy = socketdll.memcpy
memcpy.argtypes = [c_void_p, c_void_p, size_t]
memcpy.restype = c_void_p

socketpair_t = ARRAY(c_int, 2)
socketpair = socketdll.socketpair
socketpair.argtypes = [c_int, c_int, c_int, POINTER(c_int)]
socketpair.restype = c_int

shutdown = socketdll.shutdown
shutdown.argtypes = [c_int, c_int]
shutdown.restype = c_int
