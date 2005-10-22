"""
Annotation support for interp-level socket objects.
"""

import _socket
from pypy.rpython.extfunctable import declare

module = 'pypy.module._socket.rpython.ll__socket'

# ____________________________________________________________
# Built-in functions needed in the rtyper

declare(_socket.gethostname, str, '%s/gethostname' % module)

declare(_socket.ntohs, int, '%s/ntohs' % module)
declare(_socket.htons, int, '%s/ntohs' % module)
declare(_socket.ntohl, int, '%s/ntohl' % module)
declare(_socket.htonl, int, '%s/htonl' % module)
