
from pypy.rpython.tool.rfficache import *
from pypy.rpython.lltypesystem import rffi
from pypy.tool.udir import udir

def test_sizeof_c_type():
    sizeofchar = sizeof_c_type('char')
    assert sizeofchar == 1

def test_types_present():
    for name in rffi.TYPES:
        if name.startswith('unsigned'):
            name = 'u' + name[9:]
        name = name.replace(' ', '')
        assert hasattr(rffi, 'r_' + name)
        assert hasattr(rffi, name.upper())

