import os
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool import util      # ctypes.util from 0.9.9.6
from ctypes import *

includes = ('sys/types.h',
            'sys/socket.h',
            'netinet/in.h',
            'netdb.h',
            'arpa/inet.h',
            )
HEADER = ''.join(['#include <%s>\n' % filename for filename in includes])
constants = {}

# constants
for name in ['AF_INET',
             'AF_UNSPEC',
             'SOCK_STREAM',
             'SOCK_DGRAM',
             'NI_MAXHOST',
             'NI_NUMERICHOST',
             ]:
    constants[name] = ctypes_platform.getconstantinteger(name, HEADER)

# types
uint16_t = ctypes_platform.getsimpletype('uint16_t', HEADER, c_ushort)
uint32_t = ctypes_platform.getsimpletype('uint32_t', HEADER, c_uint)
size_t = ctypes_platform.getsimpletype('size_t', HEADER, c_int)
size_t = ctypes_platform.getsimpletype('size_t', HEADER, c_int)
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

# functions
dllname = util.find_library('c')
assert dllname is not None
socketdll = cdll.LoadLibrary(dllname)

errno = c_int.in_dll(socketdll, 'errno')

socket = socketdll.socket
socket.argtypes = [c_int, c_int, c_int]
socket.restype = c_int

socketclose = os.close

socketconnect = socketdll.connect
socketconnect.argtypes = [c_int, POINTER(sockaddr), socklen_t]
socketconnect.restype = c_int

getaddrinfo = socketdll.getaddrinfo
getaddrinfo.argtypes = [c_char_p, c_char_p, POINTER(addrinfo),
                        POINTER(POINTER(addrinfo))]
getaddrinfo.restype = c_int

freeaddrinfo = socketdll.freeaddrinfo
freeaddrinfo.argtypes = [POINTER(addrinfo)]
freeaddrinfo.restype = None

getnameinfo = socketdll.getnameinfo
getnameinfo.argtypes = [POINTER(sockaddr), socklen_t,
                        c_char_p, size_t,
                        c_char_p, size_t, c_int]
getnameinfo.restype = c_int

htonl = socketdll.htonl
htonl.argtypes = [uint32_t]
htonl.restype = uint32_t

htons = socketdll.htonl
htons.argtypes = [uint16_t]
htons.restype = uint16_t

ntohl = socketdll.htonl
ntohl.argtypes = [uint32_t]
ntohl.restype = uint32_t

ntohs = socketdll.htonl
ntohs.argtypes = [uint16_t]
ntohs.restype = uint16_t

inet_aton = socketdll.inet_aton
inet_aton.argtypes = [c_char_p, POINTER(in_addr)]
inet_aton.restype = c_int

socketaccept = socketdll.accept
socketaccept.argtypes = [c_int, POINTER(sockaddr), POINTER(socklen_t)]
socketaccept.restype = c_int
