"""
Annotation support for interp-level socket objects.
"""

import _socket
from pypy.module._socket.rpython import rsocket
from pypy.rpython.extfunctable import declare, declareptrtype
from pypy.annotation.model import Constant, SomeTuple, SomeList, SomeInteger, SomeString
from pypy.annotation.listdef import ListDef
from pypy.annotation.model import unionof

module = 'pypy.module._socket.rpython.ll__socket'

# ____________________________________________________________
# Built-in functions needed in the rtyper

def ann_addrinfo(*s_args):
    # Address info is a tuple: (family, socktype, proto, canonname, sockaddr)
    # where sockaddr is either a 2-tuple or a 4-tuple
    addrinfo = SomeTuple([SomeInteger(),
                          SomeInteger(),
                          SomeInteger(),
                          SomeString(),
                          SomeString(),
                          SomeInteger(),
                          SomeInteger(),
                          SomeInteger(),
                          ])
    return addrinfo

declare(_socket.gethostname, str, '%s/gethostname' % module)

declare(rsocket.getaddrinfo, rsocket.ADDRINFO, '%s/getaddrinfo' % module)
declareptrtype(rsocket.ADDRINFO, "ADDRINFO",
               nextinfo = (ann_addrinfo, '%s/nextaddrinfo' % module),
               free     = (type(None), '%s/freeaddrinfo' % module))

declare(_socket.ntohs, int, '%s/ntohs' % module)
declare(_socket.htons, int, '%s/ntohs' % module)
declare(_socket.ntohl, int, '%s/ntohl' % module)
declare(_socket.htonl, int, '%s/htonl' % module)
