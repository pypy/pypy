"""
The decoder for the bytecode of the host Python.
"""
from rpython.flowspace.decode_py27 import Py2Decoder as HostDecoder


def decode_code(code):
    """Decode a host code object into a FlowCode."""
    return HostDecoder(code).decode()
