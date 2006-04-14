import os
from pypy.rpython.rctypes import ctypes_platform
from ctypes import *

includes = ('sys/types.h', 'sys/socket.h', 'netinet/in.h', 'netdb.h')
HEADER = ''.join(['#include <%s>\n' % filename for filename in includes])
constants = {}

# constants
for name in ['AF_INET',
             'SOCK_STREAM',
             'SOCK_DGRAM',
             ]:
    constants[name] = ctypes_platform.getconstantinteger(name, HEADER)

# types
sockaddr = ctypes_platform.getstruct('struct sockaddr', HEADER,
                                     [('sa_family', c_int),
                                      # unknown and variable fields follow
                                      ])
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
socketdll = cdll.load('libc.so.6')

socket = socketdll.socket
socket.argtypes = [c_int, c_int, c_int]
socket.restype = c_int

socketclose = os.close

getaddrinfo = socketdll.getaddrinfo
getaddrinfo.argtypes = [c_char_p, c_char_p, POINTER(addrinfo),
                        POINTER(POINTER(addrinfo))]
getaddrinfo.restype = c_int

freeaddrinfo = socketdll.freeaddrinfo
freeaddrinfo.argtypes = [POINTER(addrinfo)]
freeaddrinfo.restype = None
