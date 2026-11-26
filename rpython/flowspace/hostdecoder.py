"""
The decoder for the bytecode of the host Python.
"""
import sys

from rpython.tool.twothree import PY2

if PY2:
    from rpython.flowspace.decode_py27 import Py2Decoder as HostDecoder
elif (sys.version_info[:2] == (3, 11) and
        '__pypy__' in sys.builtin_module_names):
    from rpython.flowspace.decode_pypy311 import (
        PyPy311Decoder as HostDecoder)
else:
    HostDecoder = None


def decode_code(code):
    """Decode a host code object into a FlowCode."""
    if HostDecoder is None:
        raise NotImplementedError(
            "the flow space has no decoder for the bytecode of this Python")
    return HostDecoder(code).decode()
