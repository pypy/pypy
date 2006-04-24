import os
import distutils
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool import util      # ctypes.util from 0.9.9.6
from ctypes import *

includes = ('sys/types.h',
            'sys/socket.h',
            'netinet/in.h',
            'netinet/tcp.h',
            'unistd.h',
            'stdio.h',
            'netdb.h',
            'arpa/inet.h'
            )
HEADER = ''.join(['#include <%s>\n' % filename for filename in includes])
constants = {"BDADDR_ANY": "00:00:00:00:00:00",
             "BDADDR_LOCAL": "00:00:00:FF:FF:FF"}

# constants
for name in ['AF_APPLETALK', 'AF_ASH', 'AF_ATMPVC', 'AF_ATMSVC', 'AF_AX25',
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
'TCP_NODELAY', 'AF_DECnet']:
    try:
        constants[name] = ctypes_platform.getconstantinteger(name, HEADER)
    except distutils.errors.CompileError:
        pass

for special, default in [('SOL_IP', 0),
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
                         ('SHUT_RDWR', 2)]:
    try:
        constants[special] = ctypes_platform.getconstantinteger(special, HEADER)
    except distutils.errors.CompileError:
        constants[special] = default

# types
uint16_t = ctypes_platform.getsimpletype('uint16_t', HEADER, c_ushort)
uint32_t = ctypes_platform.getsimpletype('uint32_t', HEADER, c_uint)
size_t = ctypes_platform.getsimpletype('size_t', HEADER, c_int)
ssize_t = ctypes_platform.getsimpletype('ssize_t', HEADER, c_int)
socklen_t = ctypes_platform.getsimpletype('socklen_t', HEADER, c_int)

# struct types
sockaddr = ctypes_platform.getstruct('struct sockaddr', HEADER,
                                     [('sa_family', c_int),
                                      # unknown and variable fields follow
                                      ])
sockaddr_ptr = POINTER(sockaddr)
in_addr = ctypes_platform.getstruct('struct in_addr', HEADER,
                                    [('s_addr', c_uint)])
sockaddr_in = ctypes_platform.getstruct('struct sockaddr_in', HEADER,
                                        [('sin_family', c_int),
                                         ('sin_port',   c_ushort),
                                         ('sin_addr',   in_addr)])
addrinfo_ptr = POINTER("addrinfo")
addrinfo = ctypes_platform.getstruct('struct addrinfo', HEADER,
                                     [('ai_flags', c_int),
                                      ('ai_family', c_int),
                                      ('ai_socktype', c_int),
                                      ('ai_protocol', c_int),
                                      ('ai_addrlen', c_int),
                                      ('ai_addr', POINTER(sockaddr)),
                                      ('ai_canonname', c_char_p),
                                      ('ai_next', addrinfo_ptr)])
SetPointerType(addrinfo_ptr, addrinfo)

FILE_ptr = ctypes_platform.getstruct('FILE *', HEADER,
                                     [])

# functions
dllname = util.find_library('c')
assert dllname is not None
socketdll = cdll.LoadLibrary(dllname)

errno = c_int.in_dll(socketdll, 'errno')
strerror = socketdll.strerror
strerror.argtypes = [c_int]
strerror.restype = c_char_p

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

socketaccept = socketdll.accept
socketaccept.argtypes = [c_int, sockaddr_ptr, POINTER(socklen_t)]
socketaccept.restype = c_int

socketbind = socketdll.bind
socketbind.argtypes = [c_int, sockaddr_ptr, socklen_t]
socketbind.restype = c_int

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

socketrecvfrom = socketdll.recvfrom
socketrecvfrom.argtypes = [c_int, c_void_p, size_t,
                           c_int, sockaddr_ptr, POINTER(socklen_t)]
socketrecvfrom.restype = ssize_t

socketsend = socketdll.send
socketsend.argtypes = [c_int,
                       c_void_p, #this should be constant
                       size_t, c_int]
socketsend.restype = ssize_t

socketsendto = socketdll.sendto
socketsendto.argtypes = [c_int, c_void_p, #this should be constant
                         size_t, c_int, sockaddr_ptr, #this should be const
                         socklen_t]
socketsendto.restype = ssize_t

socketshutdown = socketdll.shutdown
socketshutdown.argtypes = [c_int, c_int]
socketshutdown.restype = c_int
