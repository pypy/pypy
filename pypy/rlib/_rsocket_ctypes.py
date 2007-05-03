import os

from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool import util      # ctypes.util from 0.9.9.6

# Not used here, but exported for other code.
from pypy.rpython.rctypes.aerrno import geterrno

from ctypes import c_ushort, c_int, c_uint, c_char_p, c_void_p, c_char, c_ubyte
from ctypes import c_short, c_long, c_ulong
from ctypes import POINTER, ARRAY, cdll, sizeof, SetPointerType
from pypy.rlib.rarithmetic import intmask, r_uint

# Also not used here, but exported for other code.
from ctypes import cast, pointer, create_string_buffer

_POSIX = os.name == "posix"
_MS_WINDOWS = os.name == "nt"

if _POSIX:
    includes = ('sys/types.h',
                'sys/socket.h',
                'sys/un.h',
                'sys/poll.h',
                'sys/select.h',
                'netinet/in.h',
                'netinet/tcp.h',
                'unistd.h',
                'fcntl.h',
                'stdio.h',
                'netdb.h',
                'arpa/inet.h',
                'stdint.h', 
                'errno.h',
                )
    cond_includes = [('AF_NETLINK', 'linux/netlink.h')]
    HEADER = ''.join(['#include <%s>\n' % filename for filename in includes])
    COND_HEADER = ''.join(['#ifdef %s\n#include <%s>\n#endif\n' % cond_include
                          for cond_include in cond_includes])
if _MS_WINDOWS:
    HEADER = '\n'.join([
        '#include <WinSock2.h>',
        '#include <WS2tcpip.h>',
        # winsock2 defines AF_UNIX, but not sockaddr_un
        '#undef AF_UNIX',
        # these types do not exist on windows
        'typedef int ssize_t;',
        'typedef unsigned __int16 uint16_t;',
        'typedef unsigned __int32 uint32_t;',
        ])
    COND_HEADER = ''
constants = {}

class CConfig:
    _header_ = HEADER + COND_HEADER
    # constants
    linux      = ctypes_platform.Defined('linux')
    MS_WINDOWS = ctypes_platform.Defined('_WIN32')

    O_NONBLOCK = ctypes_platform.DefinedConstantInteger('O_NONBLOCK')
    F_GETFL = ctypes_platform.DefinedConstantInteger('F_GETFL')
    F_SETFL = ctypes_platform.DefinedConstantInteger('F_SETFL')
    FIONBIO = ctypes_platform.DefinedConstantInteger('FIONBIO')

    INVALID_SOCKET = ctypes_platform.DefinedConstantInteger('INVALID_SOCKET')
    INET_ADDRSTRLEN = ctypes_platform.DefinedConstantInteger('INET_ADDRSTRLEN')
    INET6_ADDRSTRLEN= ctypes_platform.DefinedConstantInteger('INET6_ADDRSTRLEN')
    EINPROGRESS = ctypes_platform.DefinedConstantInteger('EINPROGRESS')
    WSAEINPROGRESS = ctypes_platform.DefinedConstantInteger('WSAEINPROGRESS')
    EWOULDBLOCK = ctypes_platform.DefinedConstantInteger('EWOULDBLOCK')
    WSAEWOULDBLOCK = ctypes_platform.DefinedConstantInteger('WSAEWOULDBLOCK')
    EAFNOSUPPORT = ctypes_platform.DefinedConstantInteger('EAFNOSUPPORT')
    WSAEAFNOSUPPORT = ctypes_platform.DefinedConstantInteger('WSAEAFNOSUPPORT')
constant_names = '''
AF_AAL5 AF_APPLETALK AF_ASH AF_ATMPVC AF_ATMSVC AF_AX25 AF_BLUETOOTH AF_BRIDGE
AD_DECnet AF_ECONET AF_INET AF_INET6 AF_IPX AF_IRDA AF_KEY AF_LLC AF_NETBEUI
AF_NETLINK AF_NETROM AF_PACKET AF_PPPOX AF_ROSE AF_ROUTE AF_SECURITY AF_SNA
AF_UNIX AF_WANPIPE AF_X25 AF_UNSPEC

AI_ADDRCONFIG AI_ALL AI_CANONNAME AI_DEFAULT AI_MASK AI_NUMERICHOST
AI_NUMERICSERV AI_PASSIVE AI_V4MAPPED AI_V4MAPPED_CFG

BTPROTO_L2CAP BTPROTO_SCO BTPROTO_RFCOMM

EAI_ADDRFAMILY EAI_AGAIN EAI_BADFLAGS EAI_BADHINTS EAI_FAIL EAI_FAMILY EAI_MAX
EAI_MEMORY EAI_NODATA EAI_NONAME EAI_OVERFLOW EAI_PROTOCOL EAI_SERVICE
EAI_SOCKTYPE EAI_SYSTEM

IPPROTO_AH IPPROTO_BIP IPPROTO_DSTOPTS IPPROTO_EGP IPPROTO_EON IPPROTO_ESP
IPPROTO_FRAGMENT IPPROTO_GGP IPPROTO_GRE IPPROTO_HELLO IPPROTO_HOPOPTS 
IPPROTO_ICMPV6 IPPROTO_IDP IPPROTO_IGMP IPPROTO_IPCOMP IPPROTO_IPIP
IPPROTO_IPV4 IPPROTO_IPV6 IPPROTO_MAX IPPROTO_MOBILE IPPROTO_ND IPPROTO_NONE
IPPROTO_PIM IPPROTO_PUP IPPROTO_ROUTING IPPROTO_RSVP IPPROTO_TCP IPPROTO_TP
IPPROTO_VRRP IPPROTO_XTP

IPV6_CHECKSUM IPV6_DONTFRAG IPV6_DSTOPTS IPV6_HOPLIMIT IPV6_HOPOPTS
IPV6_JOIN_GROUP IPV6_LEAVE_GROUP IPV6_MULTICAST_HOPS IPV6_MULTICAST_IF
IPV6_MULTICAST_LOOP IPV6_NEXTHOP IPV6_PATHMTU IPV6_PKTINFO IPV6_RECVDSTOPTS
IPV6_RECVHOPLIMIT IPV6_RECVHOPOPTS IPV6_RECVPATHMTU IPV6_RECVPKTINFO
IPV6_RECVRTHDR IPV6_RECVTCLASS IPV6_RTHDR IPV6_RTHDRDSTOPTS IPV6_RTHDR_TYPE_0
IPV6_TCLASS IPV6_UNICAST_HOPS IPV6_USE_MIN_MTU IPV6_V6ONLY

IP_ADD_MEMBERSHIP IP_DEFAULT_MULTICAST_LOOP IP_DEFAULT_MULTICAST_TTL
IP_DROP_MEMBERSHIP IP_HDRINCL IP_MAX_MEMBERSHIPS IP_MULTICAST_IF
IP_MULTICAST_LOOP IP_MULTICAST_TTL IP_OPTIONS IP_RECVDSTADDR IP_RECVOPTS
IP_RECVRETOPTS IP_RETOPTS IP_TOS IP_TTL

MSG_BTAG MSG_ETAG MSG_CTRUNC MSG_DONTROUTE MSG_DONTWAIT MSG_EOR MSG_OOB
MSG_PEEK MSG_TRUNC MSG_WAITALL

NI_DGRAM NI_MAXHOST NI_MAXSERV NI_NAMEREQD NI_NOFQDN NI_NUMERICHOST
NI_NUMERICSERV

NETLINK_ROUTE NETLINK_SKIP NETLINK_W1 NETLINK_USERSOCK NETLINK_FIREWALL
NETLINK_TCPDIAG NETLINK_NFLOG NETLINK_XFRM NETLINK_ARPD NETLINK_ROUTE6
NETLINK_IP6_FW NETLINK_DNRTMSG NETLINK_TAPBASE


PACKET_HOST PACKET_BROADCAST PACKET_MULTICAST PACKET_OTHERHOST PACKET_OUTGOING
PACKET_LOOPBACK PACKET_FASTROUTE


SOCK_DGRAM SOCK_RAW SOCK_RDM SOCK_SEQPACKET SOCK_STREAM

SOL_SOCKET SOL_IPX SOL_AX25 SOL_ATALK SOL_NETROM SOL_ROSE 

SO_ACCEPTCONN SO_BROADCAST SO_DEBUG SO_DONTROUTE SO_ERROR SO_EXCLUSIVEADDRUSE
SO_KEEPALIVE SO_LINGER SO_OOBINLINE SO_RCVBUF SO_RCVLOWAT SO_RCVTIMEO
SO_REUSEADDR SO_REUSEPORT SO_SNDBUF SO_SNDLOWAT SO_SNDTIMEO SO_TYPE
SO_USELOOPBACK

TCP_CORK TCP_DEFER_ACCEPT TCP_INFO TCP_KEEPCNT TCP_KEEPIDLE TCP_KEEPINTVL
TCP_LINGER2 TCP_MAXSEG TCP_NODELAY TCP_QUICKACK TCP_SYNCNT TCP_WINDOW_CLAMP

IPX_TYPE

POLLIN POLLPRI POLLOUT POLLERR POLLHUP POLLNVAL
POLLRDNORM POLLRDBAND POLLWRNORM POLLWEBAND POLLMSG

FD_READ FD_WRITE FD_ACCEPT FD_CONNECT FD_CLOSE
WSA_WAIT_TIMEOUT WSA_WAIT_FAILED INFINITE
FD_CONNECT_BIT FD_CLOSE_BIT
'''.split()

for name in constant_names:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
    
constants["BDADDR_ANY"] =  "00:00:00:00:00:00"
constants["BDADDR_LOCAL"] = "00:00:00:FF:FF:FF"

constants_w_defaults = [('SOL_IP', 0),
                        ('SOL_TCP', 6),
                        ('SOL_UDP', 17),
                        ('SOMAXCONN', 5),
                        ('IPPROTO_IP', 6),
                        ('IPPROTO_ICMP', 1),
                        ('IPPROTO_TCP', 6),
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
                        ('SHUT_RDWR', 2),
                        ('POLLIN', 1),
                        ('POLLPRI', 2),
                        ('POLLOUT', 4),
                        ('POLLERR', 8),
                        ('POLLHUP', 16),
                        ]
for name, default in constants_w_defaults:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
    
# types
CConfig.uint16_t = ctypes_platform.SimpleType('uint16_t', c_ushort)
CConfig.uint32_t = ctypes_platform.SimpleType('uint32_t', c_uint)
CConfig.size_t = ctypes_platform.SimpleType('size_t', c_int)
CConfig.ssize_t = ctypes_platform.SimpleType('ssize_t', c_int)
CConfig.socklen_t = ctypes_platform.SimpleType('socklen_t', c_int)

if _MS_WINDOWS:
    socketfd_type = c_uint
else:
    socketfd_type = c_int

# struct types
CConfig.sockaddr = ctypes_platform.Struct('struct sockaddr',
                                             [('sa_family', c_int),
                                              ('sa_data', c_char * 0)])
sockaddr_ptr = POINTER('sockaddr')
CConfig.in_addr = ctypes_platform.Struct('struct in_addr',
                                         [('s_addr', c_uint)])
CConfig.in6_addr = ctypes_platform.Struct('struct in6_addr',
                                          [])
CConfig.sockaddr_in = ctypes_platform.Struct('struct sockaddr_in',
                                        [('sin_family', c_int),
                                         ('sin_port',   c_ushort),
                                         ('sin_addr',   CConfig.in_addr)])

CConfig.sockaddr_in6 = ctypes_platform.Struct('struct sockaddr_in6',
                                              [('sin6_family', c_int),
                                               ('sin6_port',   c_ushort),
                                               ('sin6_addr', CConfig.in6_addr),
                                               ('sin6_flowinfo', c_int),
                                               ('sin6_scope_id', c_int)])

CConfig.sockaddr_un = ctypes_platform.Struct('struct sockaddr_un',
                                             [('sun_family', c_int),
                                              ('sun_path', c_ubyte * 0)],
                                             ifdef='AF_UNIX')

CConfig.sockaddr_nl = ctypes_platform.Struct('struct sockaddr_nl',
                                             [('nl_family', c_int),
                                              ('nl_pid', c_int),
                                              ('nl_groups', c_int)],
                                             ifdef='AF_NETLINK')
                                             

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
                                      ('h_addr_list', POINTER(c_void_p)),
                                      ])


CConfig.servent = ctypes_platform.Struct('struct servent',
                                         [('s_name', c_char_p),
                                          ('s_port', c_int),
                                          ('s_proto', c_char_p),
                                          ])

CConfig.protoent = ctypes_platform.Struct('struct protoent',
                                          [('p_proto', c_int),
                                           ])

if _POSIX:
    CConfig.nfds_t = ctypes_platform.SimpleType('nfds_t')
    CConfig.pollfd = ctypes_platform.Struct('struct pollfd',
                                            [('fd', socketfd_type),
                                             ('events', c_short),
                                             ('revents', c_short)])
if _MS_WINDOWS:
    CConfig.WSAEVENT = ctypes_platform.SimpleType('WSAEVENT', c_void_p)
    CConfig.WSANETWORKEVENTS = ctypes_platform.Struct('WSANETWORKEVENTS',
                                  [('lNetworkEvents', c_long),
                                   ('iErrorCode', c_int * 10), #FD_MAX_EVENTS
                                   ])
    

CConfig.timeval = ctypes_platform.Struct('struct timeval',
                                         [('tv_sec', c_long),
                                          ('tv_usec', c_long)])

if _MS_WINDOWS:
    CConfig.fd_set = ctypes_platform.Struct('struct fd_set',
                                   [('fd_count', c_uint),
                                   # XXX use FD_SETSIZE
                                   ('fd_array', socketfd_type * 64)])

if _MS_WINDOWS:
    CConfig.WSAData = ctypes_platform.Struct('struct WSAData',
                                     [('wVersion', c_ushort),
                                      ('wHighVersion', c_ushort),
                                      ('szDescription', c_char * 1), # (WSADESCRIPTION_LEN+1)
                                      ('szSystemStatus', c_char * 1), # (WSASYS_STATUS_LEN+1)
                                      ('iMaxSockets', c_ushort),
                                      ('iMaxUdpDg', c_ushort),
                                      ('lpVendorInfo', c_char_p)])


class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))

# HACK HACK HACK
if _MS_WINDOWS:
    from ctypes import Structure
    for struct in cConfig.__dict__.values():
        if isinstance(struct, type) and issubclass(struct, Structure):
            if struct.__name__ == 'in6_addr':
                struct.__name__ = '_in6_addr'
            else:
                struct._external_ = True       # hack to avoid redeclaration of the struct in C

# fill in missing constants with reasonable defaults
cConfig.NI_MAXHOST = cConfig.NI_MAXHOST or 1025
cConfig.NI_MAXSERV = cConfig.NI_MAXSERV or 32
cConfig.INET_ADDRSTRLEN = cConfig.INET_ADDRSTRLEN or 16

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
for name, value in constants.items():
    if isinstance(value, long):
        if r_uint(value) == value:
            constants[name] = intmask(value)

locals().update(constants)

O_NONBLOCK = cConfig.O_NONBLOCK
F_GETFL = cConfig.F_GETFL
F_SETFL = cConfig.F_SETFL
FIONBIO = cConfig.FIONBIO
INET_ADDRSTRLEN = cConfig.INET_ADDRSTRLEN
INET6_ADDRSTRLEN = cConfig.INET6_ADDRSTRLEN
EINPROGRESS = cConfig.EINPROGRESS or cConfig.WSAEINPROGRESS
EWOULDBLOCK = cConfig.EWOULDBLOCK or cConfig.WSAEWOULDBLOCK
EAFNOSUPPORT = cConfig.EAFNOSUPPORT or cConfig.WSAEAFNOSUPPORT

linux = cConfig.linux
MS_WINDOWS = cConfig.MS_WINDOWS
assert MS_WINDOWS == _MS_WINDOWS

if MS_WINDOWS:
    def invalid_socket(fd):
        return fd == INVALID_SOCKET
    INVALID_SOCKET = cConfig.INVALID_SOCKET
else:
    def invalid_socket(fd):
        return fd < 0
    INVALID_SOCKET = -1

uint16_t = cConfig.uint16_t
uint32_t = cConfig.uint32_t
size_t = cConfig.size_t
ssize_t = cConfig.ssize_t
socklen_t = cConfig.socklen_t
sockaddr = cConfig.sockaddr
sockaddr_size = sizeof(sockaddr)
sockaddr_in = cConfig.sockaddr_in
sockaddr_in6 = cConfig.sockaddr_in6
sockaddr_un = cConfig.sockaddr_un
if cConfig.sockaddr_nl is not None:
    sockaddr_nl = cConfig.sockaddr_nl
in_addr = cConfig.in_addr
in_addr_size = sizeof(in_addr)
in6_addr = cConfig.in6_addr
addrinfo = cConfig.addrinfo
if _POSIX:
    nfds_t = cConfig.nfds_t
    pollfd = cConfig.pollfd
if MS_WINDOWS:
    WSAEVENT = cConfig.WSAEVENT
    WSANETWORKEVENTS = cConfig.WSANETWORKEVENTS
timeval = cConfig.timeval
if MS_WINDOWS:
    fd_set = cConfig.fd_set

c_int_size = sizeof(c_int)
SetPointerType(addrinfo_ptr, addrinfo)
SetPointerType(sockaddr_ptr, sockaddr)


# functions
if MS_WINDOWS:
    from ctypes import windll
    dllname = util.find_library('ws2_32')
    assert dllname is not None
    socketdll = windll.LoadLibrary(dllname)
else:
    dllname = util.find_library('c')
    assert dllname is not None
    socketdll = cdll.LoadLibrary(dllname)

if _POSIX:
    dup = socketdll.dup
    dup.argtypes = [socketfd_type]
    dup.restype = socketfd_type

#errno = c_int.in_dll(socketdll, 'errno')

if _POSIX:
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
socket.restype = socketfd_type

if MS_WINDOWS:
    socketclose = socketdll.closesocket
else:
    socketclose = socketdll.close
socketclose.argtypes = [socketfd_type]
socketclose.restype = c_int

socketconnect = socketdll.connect
socketconnect.argtypes = [socketfd_type, sockaddr_ptr, socklen_t]
socketconnect.restype = c_int

if not MS_WINDOWS:
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

if _POSIX:
    inet_aton = socketdll.inet_aton
    inet_aton.argtypes = [c_char_p, POINTER(in_addr)]
    inet_aton.restype = c_int

inet_ntoa = socketdll.inet_ntoa
inet_ntoa.argtypes = [in_addr]
inet_ntoa.restype = c_char_p

if _POSIX:
    inet_pton = socketdll.inet_pton
    inet_pton.argtypes = [c_int, c_char_p, c_void_p]
    inet_pton.restype = c_int

    inet_ntop = socketdll.inet_ntop
    inet_ntop.argtypes = [c_int, c_void_p, c_char_p, socklen_t]
    inet_ntop.restype = c_char_p

inet_addr = socketdll.inet_addr
inet_addr.argtypes = [c_char_p]
inet_addr.restype = c_uint

socketaccept = socketdll.accept
socketaccept.argtypes = [socketfd_type, sockaddr_ptr, POINTER(socklen_t)]
socketaccept.restype = socketfd_type

socketbind = socketdll.bind
socketbind.argtypes = [socketfd_type, sockaddr_ptr, socklen_t]
socketbind.restype = c_int

socketlisten = socketdll.listen
socketlisten.argtypes = [socketfd_type, c_int]
socketlisten.restype = c_int

socketgetpeername = socketdll.getpeername
socketgetpeername.argtypes = [socketfd_type, sockaddr_ptr, POINTER(socklen_t)]
socketgetpeername.restype = c_int

socketgetsockname = socketdll.getsockname
socketgetsockname.argtypes = [socketfd_type, sockaddr_ptr, POINTER(socklen_t)]
socketgetsockname.restype = c_int

socketgetsockopt = socketdll.getsockopt
socketgetsockopt.argtypes = [socketfd_type, c_int, c_int, 
                             c_void_p, POINTER(socklen_t)]
socketgetsockopt.restype = c_int

socketsetsockopt = socketdll.setsockopt
socketsetsockopt.argtypes = [socketfd_type, c_int, c_int,
                             c_void_p, #this should be constant
                             socklen_t]
socketsetsockopt.restype = c_int

socketrecv = socketdll.recv
socketrecv.argtypes = [socketfd_type, c_void_p, c_int, c_int]
socketrecv.recv = ssize_t

recvfrom = socketdll.recvfrom
recvfrom.argtypes = [socketfd_type, c_void_p, size_t,
                     c_int, sockaddr_ptr, POINTER(socklen_t)]
recvfrom.restype = ssize_t

send = socketdll.send
send.argtypes = [socketfd_type,
                       c_void_p, #this should be constant
                       size_t, c_int]
send.restype = ssize_t

sendto = socketdll.sendto
sendto.argtypes = [socketfd_type, c_void_p, #this should be constant
                         size_t, c_int, sockaddr_ptr, #this should be const
                         socklen_t]
sendto.restype = ssize_t

socketshutdown = socketdll.shutdown
socketshutdown.argtypes = [socketfd_type, c_int]
socketshutdown.restype = c_int

gethostname = socketdll.gethostname
gethostname.argtypes = [c_char_p, c_int]
gethostname.restype = c_int

gethostbyname = socketdll.gethostbyname
gethostbyname.argtypes = [c_char_p]
gethostbyname.restype = POINTER(cConfig.hostent)

gethostbyaddr = socketdll.gethostbyaddr
gethostbyaddr.argtypes = [c_void_p, c_int, c_int]
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

if _POSIX:
    fcntl = socketdll.fcntl
    fcntl.argtypes = [socketfd_type, c_int, c_int]
    fcntl.restype = c_int

    socketpair_t = ARRAY(socketfd_type, 2)
    socketpair = socketdll.socketpair
    socketpair.argtypes = [c_int, c_int, c_int, POINTER(socketpair_t)]
    socketpair.restype = c_int

if _MS_WINDOWS:
    ioctlsocket = socketdll.ioctlsocket
    ioctlsocket.argtypes = [socketfd_type, c_long, POINTER(c_ulong)]
    ioctlsocket.restype = c_int
    

shutdown = socketdll.shutdown
shutdown.argtypes = [c_int, c_int]
shutdown.restype = c_int

if _POSIX:
    poll = socketdll.poll
    poll.argtypes = [POINTER(pollfd), nfds_t, c_int]
    poll.restype = c_int
elif MS_WINDOWS:
    select = socketdll.select
    select.argtypes = [c_int,
                       POINTER(fd_set), POINTER(fd_set), POINTER(fd_set),
                       POINTER(timeval)]
    select.restype = c_int

    WSACreateEvent = socketdll.WSACreateEvent
    WSACreateEvent.argtypes = []
    WSACreateEvent.restype = WSAEVENT

    WSACloseEvent = socketdll.WSACloseEvent
    WSACloseEvent.argtypes = [WSAEVENT]
    WSACloseEvent.restype = c_int

    WSAEventSelect = socketdll.WSAEventSelect
    WSAEventSelect.argtypes = [socketfd_type, WSAEVENT, c_long]
    WSAEventSelect.restype = c_int

    WSAWaitForMultipleEvents = socketdll.WSAWaitForMultipleEvents
    WSAWaitForMultipleEvents.argtypes = [c_long, POINTER(WSAEVENT),
                                         c_int, c_long, c_int]
    WSAWaitForMultipleEvents.restype = c_long

    WSAEnumNetworkEvents = socketdll.WSAEnumNetworkEvents
    WSAEnumNetworkEvents.argtypes = [socketfd_type, WSAEVENT,
                                     POINTER(WSANETWORKEVENTS)]
    WSAEnumNetworkEvents.restype = c_int

if MS_WINDOWS:
    WSAData = cConfig.WSAData
    WSAStartup = socketdll.WSAStartup
    WSAStartup.argtypes = [c_int, POINTER(WSAData)]
    WSAStartup.restype = c_int
    WSAStartup.libraries = ('ws2_32',)

    WSAGetLastError = socketdll.WSAGetLastError
    WSAGetLastError.argtypes = []
    WSAGetLastError.restype = c_int
    geterrno = WSAGetLastError
    
    import errno
    WIN32_ERROR_MESSAGES = {
        errno.WSAEINTR:  "Interrupted system call",
        errno.WSAEBADF:  "Bad file descriptor",
        errno.WSAEACCES: "Permission denied",
        errno.WSAEFAULT: "Bad address",
        errno.WSAEINVAL: "Invalid argument",
        errno.WSAEMFILE: "Too many open files",
        errno.WSAEWOULDBLOCK:
          "The socket operation could not complete without blocking",
        errno.WSAEINPROGRESS: "Operation now in progress",
        errno.WSAEALREADY: "Operation already in progress",
        errno.WSAENOTSOCK: "Socket operation on non-socket",
        errno.WSAEDESTADDRREQ: "Destination address required",
        errno.WSAEMSGSIZE: "Message too long",
        errno.WSAEPROTOTYPE: "Protocol wrong type for socket",
        errno.WSAENOPROTOOPT: "Protocol not available",
        errno.WSAEPROTONOSUPPORT: "Protocol not supported",
        errno.WSAESOCKTNOSUPPORT: "Socket type not supported",
        errno.WSAEOPNOTSUPP: "Operation not supported",
        errno.WSAEPFNOSUPPORT: "Protocol family not supported",
        errno.WSAEAFNOSUPPORT: "Address family not supported",
        errno.WSAEADDRINUSE: "Address already in use",
        errno.WSAEADDRNOTAVAIL: "Can't assign requested address",
        errno.WSAENETDOWN: "Network is down",
        errno.WSAENETUNREACH: "Network is unreachable",
        errno.WSAENETRESET: "Network dropped connection on reset",
        errno.WSAECONNABORTED: "Software caused connection abort",
        errno.WSAECONNRESET: "Connection reset by peer",
        errno.WSAENOBUFS: "No buffer space available",
        errno.WSAEISCONN: "Socket is already connected",
        errno.WSAENOTCONN: "Socket is not connected",
        errno.WSAESHUTDOWN: "Can't send after socket shutdown",
        errno.WSAETOOMANYREFS: "Too many references: can't splice",
        errno.WSAETIMEDOUT: "Operation timed out",
        errno.WSAECONNREFUSED: "Connection refused",
        errno.WSAELOOP: "Too many levels of symbolic links",
        errno.WSAENAMETOOLONG: "File name too long",
        errno.WSAEHOSTDOWN: "Host is down",
        errno.WSAEHOSTUNREACH: "No route to host",
        errno.WSAENOTEMPTY: "Directory not empty",
        errno.WSAEPROCLIM: "Too many processes",
        errno.WSAEUSERS: "Too many users",
        errno.WSAEDQUOT: "Disc quota exceeded",
        errno.WSAESTALE: "Stale NFS file handle",
        errno.WSAEREMOTE: "Too many levels of remote in path",
        errno.WSASYSNOTREADY: "Network subsystem is unvailable",
        errno.WSAVERNOTSUPPORTED: "WinSock version is not supported",
        errno.WSANOTINITIALISED: "Successful WSAStartup() not yet performed",
        errno.WSAEDISCON: "Graceful shutdown in progress",

        # Resolver errors
        # XXX Not exported by errno. Replace by the values in winsock.h
        # errno.WSAHOST_NOT_FOUND: "No such host is known",
        # errno.WSATRY_AGAIN: "Host not found, or server failed",
        # errno.WSANO_RECOVERY: "Unexpected server error encountered",
        # errno.WSANO_DATA: "Valid name without requested data",
        # errno.WSANO_ADDRESS: "No address, look for MX record",
        }

    def socket_strerror(errno):
        return WIN32_ERROR_MESSAGES.get(errno, "winsock error %d" % errno)
else:
    def socket_strerror(errno):
        return strerror(errno)
