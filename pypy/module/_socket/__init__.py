# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
import _socket
import sys

class Module(MixedModule):
    appleveldefs = {
        'error'      : 'app_socket.error',
        'herror'     : 'app_socket.herror',
        'gaierror'   : 'app_socket.gaierror',
        'timeout'    : 'app_socket.timeout',
        'setdefaulttimeout'    : 'app_socket.setdefaulttimeout',
        'getdefaulttimeout'    : 'app_socket.getdefaulttimeout',
    }

    interpleveldefs = {
    }

for name in """
    gethostbyname gethostbyname_ex gethostbyaddr gethostname
    getservbyname getservbyport getprotobyname
    fromfd socketpair
    ntohs ntohl htons htonl inet_aton inet_ntoa inet_pton inet_ntop
    getaddrinfo getnameinfo
    """.split():
    
    if hasattr(_socket, name):
        Module.interpleveldefs[name] = 'interp_socket.%s' % (name, )

for constant in dir(_socket):
    value = getattr(_socket, constant)
    if constant.isupper() and type(value) in (int, str):
        Module.interpleveldefs[constant] = "space.wrap(%s)" % value

Module.interpleveldefs['has_ipv6'] = "space.wrap(%s)" % _socket.has_ipv6
