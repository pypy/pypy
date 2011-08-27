
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem.rffi import CCHARP
from pypy.rlib.rposix import get_errno as geterrno
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform as target_platform

from pypy.rlib.rarithmetic import intmask, r_uint
import os,sys

_POSIX = os.name == "posix"
_WIN32 = sys.platform == "win32"
_MSVC  = target_platform.name == "msvc"
_MINGW = target_platform.name == "mingw32"
_SOLARIS = sys.platform == "sunos5"
_MACOSX = sys.platform == "darwin"

if _POSIX:
    includes = ('sys/types.h',
                'sys/socket.h',
                'sys/un.h',
                'sys/poll.h',
                'sys/select.h',
                'sys/types.h',
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

    cond_includes = [('AF_NETLINK', 'linux/netlink.h'),
                     ('AF_PACKET', 'netpacket/packet.h'),
                     ('AF_PACKET', 'sys/ioctl.h'),
                     ('AF_PACKET', 'net/if.h')]
    
    libraries = ()
    calling_conv = 'c'
    HEADER = ''.join(['#include <%s>\n' % filename for filename in includes])
    COND_HEADER = ''.join(['#ifdef %s\n#include <%s>\n#endif\n' % cond_include
                          for cond_include in cond_includes])

if _SOLARIS:
    libraries = libraries + ('socket', 'nsl')

if _WIN32:
    includes = ()
    libraries = ('ws2_32',)
    calling_conv = 'win'
    header_lines = [
        '#include <WinSock2.h>',
        '#include <WS2tcpip.h>',
        # winsock2 defines AF_UNIX, but not sockaddr_un
        '#undef AF_UNIX',
        ]
    if _MSVC:
        header_lines.extend([
            '#include <Mstcpip.h>',
            # these types do not exist on microsoft compilers
            'typedef int ssize_t;',
            'typedef unsigned __int16 uint16_t;',
            'typedef unsigned __int32 uint32_t;',
            ])
    else: # MINGW
        includes = ('stdint.h',)
        header_lines.extend([
            '''\
            #ifndef _WIN32_WINNT
            #define _WIN32_WINNT 0x0501
            #endif''',
            '#define SIO_RCVALL             _WSAIOW(IOC_VENDOR,1)',
            '#define SIO_KEEPALIVE_VALS     _WSAIOW(IOC_VENDOR,4)',
            '#define RCVALL_OFF             0',
            '#define RCVALL_ON              1',
            '#define RCVALL_SOCKETLEVELONLY 2',
            '''\
            struct tcp_keepalive {
                u_long  onoff;
                u_long  keepalivetime;
                u_long  keepaliveinterval;
            };'''
            ])
    HEADER = '\n'.join(header_lines)
    COND_HEADER = ''
constants = {}

eci = ExternalCompilationInfo(
    post_include_bits = [HEADER, COND_HEADER],
    includes = includes,
    libraries = libraries,
)

class CConfig:
    _compilation_info_ = eci
    # constants
    linux = platform.Defined('linux')
    WIN32 = platform.Defined('_WIN32')

    O_NONBLOCK = platform.DefinedConstantInteger('O_NONBLOCK')
    F_GETFL = platform.DefinedConstantInteger('F_GETFL')
    F_SETFL = platform.DefinedConstantInteger('F_SETFL')
    FIONBIO = platform.DefinedConstantInteger('FIONBIO')

    INVALID_SOCKET = platform.DefinedConstantInteger('INVALID_SOCKET')
    INET_ADDRSTRLEN = platform.DefinedConstantInteger('INET_ADDRSTRLEN')
    INET6_ADDRSTRLEN= platform.DefinedConstantInteger('INET6_ADDRSTRLEN')
    EINTR = platform.DefinedConstantInteger('EINTR')
    WSAEINTR = platform.DefinedConstantInteger('WSAEINTR')
    EINPROGRESS = platform.DefinedConstantInteger('EINPROGRESS')
    WSAEINPROGRESS = platform.DefinedConstantInteger('WSAEINPROGRESS')
    EWOULDBLOCK = platform.DefinedConstantInteger('EWOULDBLOCK')
    WSAEWOULDBLOCK = platform.DefinedConstantInteger('WSAEWOULDBLOCK')
    EAFNOSUPPORT = platform.DefinedConstantInteger('EAFNOSUPPORT')
    WSAEAFNOSUPPORT = platform.DefinedConstantInteger('WSAEAFNOSUPPORT')
    EISCONN = platform.DefinedConstantInteger('EISCONN')
    WSAEISCONN = platform.DefinedConstantInteger('WSAEISCONN')
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
WSA_IO_PENDING WSA_IO_INCOMPLETE WSA_INVALID_HANDLE
WSA_INVALID_PARAMETER WSA_NOT_ENOUGH_MEMORY WSA_OPERATION_ABORTED
SIO_RCVALL SIO_KEEPALIVE_VALS

SIOCGIFNAME
'''.split()

for name in constant_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

if _WIN32:
    # some SDKs define these values with an enum, #ifdef won't work
    for name in ('RCVALL_ON', 'RCVALL_OFF', 'RCVALL_SOCKETLEVELONLY'):
        setattr(CConfig, name, platform.ConstantInteger(name))
        constant_names.append(name)

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
                        ('FD_SETSIZE', 64),
                        ]
for name, default in constants_w_defaults:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

# types
if _MSVC:
    socketfd_type = rffi.UINT
else:
    socketfd_type = rffi.INT

CConfig.uint16_t = platform.SimpleType('uint16_t', rffi.USHORT)
CConfig.uint32_t = platform.SimpleType('uint32_t', rffi.UINT)
CConfig.size_t = platform.SimpleType('size_t', rffi.INT)
CConfig.ssize_t = platform.SimpleType('ssize_t', rffi.INT)
CConfig.socklen_t = platform.SimpleType('socklen_t', rffi.INT)
sockaddr_ptr = lltype.Ptr(lltype.ForwardReference())
addrinfo_ptr = lltype.Ptr(lltype.ForwardReference())

# struct types
CConfig.sockaddr = platform.Struct('struct sockaddr',
                                             [('sa_family', rffi.INT),
                                   ('sa_data', rffi.CFixedArray(rffi.CHAR, 1))])
CConfig.in_addr = platform.Struct('struct in_addr',
                                         [('s_addr', rffi.UINT)])
CConfig.in6_addr = platform.Struct('struct in6_addr',
                                          [])
CConfig.sockaddr_in = platform.Struct('struct sockaddr_in',
                                        [('sin_family', rffi.INT),
                                         ('sin_port',   rffi.USHORT),
                                         ('sin_addr',   CConfig.in_addr)])

CConfig.sockaddr_in6 = platform.Struct('struct sockaddr_in6',
                                              [('sin6_family', rffi.INT),
                                               ('sin6_port',   rffi.USHORT),
                                               ('sin6_flowinfo', rffi.INT),
                                               ('sin6_addr', CConfig.in6_addr),
                                               ('sin6_scope_id', rffi.INT)])

CConfig.sockaddr_un = platform.Struct('struct sockaddr_un',
                                             [('sun_family', rffi.INT),
                                   ('sun_path', rffi.CFixedArray(rffi.CHAR, 1))],
                                             ifdef='AF_UNIX')

CConfig.sockaddr_nl = platform.Struct('struct sockaddr_nl',
                                             [('nl_family', rffi.INT),
                                              ('nl_pid', rffi.INT),
                                              ('nl_groups', rffi.INT)],
                                             ifdef='AF_NETLINK')
                                             
CConfig.addrinfo = platform.Struct('struct addrinfo',
                                     [('ai_flags', rffi.INT),
                                      ('ai_family', rffi.INT),
                                      ('ai_socktype', rffi.INT),
                                      ('ai_protocol', rffi.INT),
                                      ('ai_addrlen', rffi.INT),
                                      ('ai_addr', sockaddr_ptr),
                                      ('ai_canonname', CCHARP),
                                      ('ai_next', addrinfo_ptr)])

CConfig.hostent = platform.Struct('struct hostent',
                                     [('h_name', CCHARP),
                                      ('h_aliases', rffi.CCHARPP),
                                      ('h_addrtype', rffi.INT),
                                      ('h_length', rffi.INT),
                                      ('h_addr_list', rffi.CCHARPP),
                                      ])


CConfig.servent = platform.Struct('struct servent',
                                         [('s_name', CCHARP),
                                          ('s_port', rffi.INT),
                                          ('s_proto', CCHARP),
                                          ])

CConfig.protoent = platform.Struct('struct protoent',
                                          [('p_proto', rffi.INT),
                                           ])

if _POSIX:
    CConfig.nfds_t = platform.SimpleType('nfds_t')
    CConfig.pollfd = platform.Struct('struct pollfd',
                                            [('fd', socketfd_type),
                                             ('events', rffi.SHORT),
                                             ('revents', rffi.SHORT)])

    CConfig.sockaddr_ll = platform.Struct('struct sockaddr_ll',
                              [('sll_ifindex', rffi.INT),
                               ('sll_protocol', rffi.INT),
                               ('sll_pkttype', rffi.INT),
                               ('sll_hatype', rffi.INT),
                               ('sll_addr', rffi.CFixedArray(rffi.CHAR, 8)),
                               ('sll_halen', rffi.INT)],
                              ifdef='AF_PACKET')

    CConfig.ifreq = platform.Struct('struct ifreq', [('ifr_ifindex', rffi.INT),
                                 ('ifr_name', rffi.CFixedArray(rffi.CHAR, 8))],
                                    ifdef='AF_PACKET')

if _WIN32:
    CConfig.WSAEVENT = platform.SimpleType('WSAEVENT', rffi.VOIDP)
    CConfig.WSANETWORKEVENTS = platform.Struct(
        'struct _WSANETWORKEVENTS',
        [('lNetworkEvents', rffi.LONG),
         ('iErrorCode', rffi.CFixedArray(rffi.INT, 10)), #FD_MAX_EVENTS
         ])

CConfig.timeval = platform.Struct('struct timeval',
                                         [('tv_sec', rffi.LONG),
                                          ('tv_usec', rffi.LONG)])

fd_set = rffi.COpaquePtr('fd_set', compilation_info=eci)

if _WIN32:
    CConfig.WSAData = platform.Struct('struct WSAData',
                                     [('wVersion', rffi.USHORT),
                                      ('wHighVersion', rffi.USHORT),
                                      ('szDescription', rffi.CFixedArray(lltype.Char, 1)), # (WSADESCRIPTION_LEN+1)
                                      ('szSystemStatus', rffi.CFixedArray(lltype.Char, 1)), # (WSASYS_STATUS_LEN+1)
                                      ('iMaxSockets', rffi.USHORT),
                                      ('iMaxUdpDg', rffi.USHORT),
                                      ('lpVendorInfo', CCHARP)])

    CConfig.tcp_keepalive = platform.Struct(
        'struct tcp_keepalive',
        [('onoff', rffi.ULONG),
         ('keepalivetime', rffi.ULONG),
         ('keepaliveinterval', rffi.ULONG)])


class cConfig:
    pass
cConfig.__dict__.update(platform.configure(CConfig))

sockaddr_ptr.TO.become(cConfig.sockaddr)
addrinfo_ptr.TO.become(cConfig.addrinfo)

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
EINTR = cConfig.EINTR or cConfig.WSAEINTR
EINPROGRESS = cConfig.EINPROGRESS or cConfig.WSAEINPROGRESS
EWOULDBLOCK = cConfig.EWOULDBLOCK or cConfig.WSAEWOULDBLOCK
EAFNOSUPPORT = cConfig.EAFNOSUPPORT or cConfig.WSAEAFNOSUPPORT
EISCONN = cConfig.EISCONN or cConfig.WSAEISCONN

linux = cConfig.linux
WIN32 = cConfig.WIN32
assert WIN32 == _WIN32

if _MSVC:
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
#sockaddr_size = sizeof(sockaddr)
sockaddr_in = cConfig.sockaddr_in
sockaddr_in6 = cConfig.sockaddr_in6
sockaddr_un = cConfig.sockaddr_un
if cConfig.sockaddr_nl is not None:
    sockaddr_nl = cConfig.sockaddr_nl
in_addr = cConfig.in_addr
#in_addr_size = sizeof(in_addr)
in6_addr = cConfig.in6_addr
addrinfo = cConfig.addrinfo
if _POSIX:
    nfds_t = cConfig.nfds_t
    pollfd = cConfig.pollfd
    if cConfig.sockaddr_ll is not None:
        sockaddr_ll = cConfig.sockaddr_ll
    ifreq = cConfig.ifreq
if WIN32:
    WSAEVENT = cConfig.WSAEVENT
    WSANETWORKEVENTS = cConfig.WSANETWORKEVENTS
timeval = cConfig.timeval

#if _POSIX:
#    includes = list(includes)
#    for _name, _header in cond_includes:
#        if getattr(cConfig, _name) is not None:
#            includes.append(_header)
#    eci = ExternalCompilationInfo(includes=includes, libraries=libraries,
#                                  separate_module_sources=sources)

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           calling_conv=calling_conv, **kwds)

def external_c(name, args, result, **kwargs):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           calling_conv='c', **kwargs)

if _POSIX:
    dup = external('dup', [socketfd_type], socketfd_type)
    gai_strerror = external('gai_strerror', [rffi.INT], CCHARP)

#h_errno = c_int.in_dll(socketdll, 'h_errno')
#
#hstrerror = socketdll.hstrerror
#hstrerror.argtypes = [c_int]
#hstrerror.restype = c_char_p

socket = external('socket', [rffi.INT, rffi.INT, rffi.INT], socketfd_type)

if WIN32:
    socketclose = external('closesocket', [socketfd_type], rffi.INT, threadsafe=False)
else:
    socketclose = external('close', [socketfd_type], rffi.INT, threadsafe=False)

socketconnect = external('connect', [socketfd_type, sockaddr_ptr, socklen_t], rffi.INT)

getaddrinfo = external('getaddrinfo', [CCHARP, CCHARP,
                        addrinfo_ptr,
                        lltype.Ptr(rffi.CArray(addrinfo_ptr))], rffi.INT)
freeaddrinfo = external('freeaddrinfo', [addrinfo_ptr], lltype.Void)
getnameinfo = external('getnameinfo', [sockaddr_ptr, socklen_t, CCHARP,
                       size_t, CCHARP, size_t, rffi.INT], rffi.INT)

htonl = external('htonl', [rffi.UINT], rffi.UINT, threadsafe=False)
htons = external('htons', [rffi.USHORT], rffi.USHORT, threadsafe=False)
ntohl = external('ntohl', [rffi.UINT], rffi.UINT, threadsafe=False)
ntohs = external('ntohs', [rffi.USHORT], rffi.USHORT, threadsafe=False)

if _POSIX:
    inet_aton = external('inet_aton', [CCHARP, lltype.Ptr(in_addr)],
                                rffi.INT)

inet_ntoa = external('inet_ntoa', [in_addr], rffi.CCHARP)

if _POSIX:
    inet_pton = external('inet_pton', [rffi.INT, rffi.CCHARP,
                                              rffi.VOIDP], rffi.INT)

    inet_ntop = external('inet_ntop', [rffi.INT, rffi.VOIDP, CCHARP,
                                              socklen_t], CCHARP)

inet_addr = external('inet_addr', [rffi.CCHARP], rffi.UINT)
socklen_t_ptr = lltype.Ptr(rffi.CFixedArray(socklen_t, 1))
socketaccept = external('accept', [socketfd_type, sockaddr_ptr,
                              socklen_t_ptr], socketfd_type)
socketbind = external('bind', [socketfd_type, sockaddr_ptr, socklen_t],
                              rffi.INT)
socketlisten = external('listen', [socketfd_type, rffi.INT], rffi.INT)
socketgetpeername = external('getpeername', [socketfd_type,
                                    sockaddr_ptr, socklen_t_ptr], rffi.INT)
socketgetsockname = external('getsockname', [socketfd_type,
                                   sockaddr_ptr, socklen_t_ptr], rffi.INT)
socketgetsockopt = external('getsockopt', [socketfd_type, rffi.INT,
                               rffi.INT, rffi.VOIDP, socklen_t_ptr], rffi.INT)
socketsetsockopt = external('setsockopt', [socketfd_type, rffi.INT,
                                   rffi.INT, rffi.VOIDP, socklen_t], rffi.INT)
socketrecv = external('recv', [socketfd_type, rffi.VOIDP, rffi.INT,
                                      rffi.INT], ssize_t)
recvfrom = external('recvfrom', [socketfd_type, rffi.VOIDP, size_t,
                           rffi.INT, sockaddr_ptr, socklen_t_ptr], rffi.INT)
send = external('send', [socketfd_type, rffi.CCHARP, size_t, rffi.INT],
                       ssize_t)
sendto = external('sendto', [socketfd_type, rffi.VOIDP, size_t, rffi.INT,
                                    sockaddr_ptr, socklen_t], ssize_t)
socketshutdown = external('shutdown', [socketfd_type, rffi.INT], rffi.INT)
gethostname = external('gethostname', [rffi.CCHARP, rffi.INT], rffi.INT)
gethostbyname = external('gethostbyname', [rffi.CCHARP],
                                lltype.Ptr(cConfig.hostent))
gethostbyaddr = external('gethostbyaddr', [rffi.VOIDP, rffi.INT, rffi.INT], lltype.Ptr(cConfig.hostent))
getservbyname = external('getservbyname', [rffi.CCHARP, rffi.CCHARP], lltype.Ptr(cConfig.servent))
getservbyport = external('getservbyport', [rffi.INT, rffi.CCHARP], lltype.Ptr(cConfig.servent))
getprotobyname = external('getprotobyname', [rffi.CCHARP], lltype.Ptr(cConfig.protoent))

if _POSIX:
    fcntl = external('fcntl', [socketfd_type, rffi.INT, rffi.INT], rffi.INT)
    socketpair_t = rffi.CArray(socketfd_type)
    socketpair = external('socketpair', [rffi.INT, rffi.INT, rffi.INT,
                          lltype.Ptr(socketpair_t)], rffi.INT)
    if ifreq is not None:
        ioctl = external('ioctl', [socketfd_type, rffi.INT, lltype.Ptr(ifreq)],
                         rffi.INT)

if _WIN32:
    ioctlsocket = external('ioctlsocket',
                           [socketfd_type, rffi.LONG, rffi.ULONGP],
                           rffi.INT)

select = external('select',
                  [rffi.INT, fd_set, fd_set,
                   fd_set, lltype.Ptr(timeval)],
                  rffi.INT)

FD_CLR = external_c('FD_CLR', [rffi.INT, fd_set], lltype.Void, macro=True)
FD_ISSET = external_c('FD_ISSET', [rffi.INT, fd_set], rffi.INT, macro=True)
FD_SET = external_c('FD_SET', [rffi.INT, fd_set], lltype.Void, macro=True)
FD_ZERO = external_c('FD_ZERO', [fd_set], lltype.Void, macro=True)

if _POSIX:
    pollfdarray = rffi.CArray(pollfd)
    poll = external('poll', [lltype.Ptr(pollfdarray), nfds_t, rffi.INT],
                    rffi.INT)
    # workaround for Mac OS/X on which poll() seems to behave a bit strangely
    # (see test_recv_send_timeout in pypy.module._socket.test.test_sock_app)
    # https://issues.apache.org/bugzilla/show_bug.cgi?id=34332
    poll_may_be_broken = _MACOSX

elif WIN32:
    from pypy.rlib import rwin32
    #
    # The following is for pypy.rlib.rpoll
    #
    WSAEVENT_ARRAY = rffi.CArray(WSAEVENT)

    WSACreateEvent = external('WSACreateEvent', [], WSAEVENT)

    WSACloseEvent = external('WSACloseEvent', [WSAEVENT], rffi.INT)

    WSAEventSelect = external('WSAEventSelect',
                              [socketfd_type, WSAEVENT, rffi.LONG],
                              rffi.INT)

    WSAWaitForMultipleEvents = external('WSAWaitForMultipleEvents',
                                        [rffi.LONG, lltype.Ptr(WSAEVENT_ARRAY),
                                         rffi.INT, rffi.LONG, rffi.INT],
                                        rffi.ULONG)

    WSAEnumNetworkEvents = external('WSAEnumNetworkEvents',
                                    [socketfd_type, WSAEVENT,
                                     lltype.Ptr(WSANETWORKEVENTS)],
                                    rffi.INT)

    WSAIoctl = external('WSAIoctl',
                        [socketfd_type, rwin32.DWORD,
                         rffi.VOIDP, rwin32.DWORD,
                         rffi.VOIDP, rwin32.DWORD,
                         rwin32.LPDWORD, rffi.VOIDP, rffi.VOIDP],
                        rffi.INT)
    tcp_keepalive = cConfig.tcp_keepalive

if WIN32:
    WSAData = cConfig.WSAData
    WSAStartup = external('WSAStartup', [rffi.INT, lltype.Ptr(WSAData)],
                          rffi.INT)

    WSAGetLastError = external('WSAGetLastError', [], rffi.INT)
    geterrno = WSAGetLastError

    from pypy.rlib import rwin32

    def socket_strerror_str(errno):
        return rwin32.FormatError(errno)
    def gai_strerror_str(errno):
        return rwin32.FormatError(errno)
else:
    socket_strerror_str = os.strerror
    def gai_strerror_str(errno):
        return rffi.charp2str(gai_strerror(errno))
