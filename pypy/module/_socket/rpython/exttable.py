"""
Annotation support for interp-level socket objects.
"""

import _socket
from pypy.rpython.extfunctable import declare

module = 'pypy.module._socket.rpython.ll__socket'

# ____________________________________________________________
# Built-in functions needed in the rtyper

declare(_socket.ntohs, int, '%s/ntohs' % module)
