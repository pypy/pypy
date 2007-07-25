
from pypy.rpython.lltypesystem.rfficache import *
from pypy.rpython.lltypesystem import rffi
from pypy.tool.udir import udir

def test_sizeof_c_type():
    sizeofchar = sizeof_c_type('char')
    assert sizeofchar == 1

def test_c_ifdefined():
    assert c_ifdefined('X', add_source='#define X')
    assert not c_ifdefined('X')

def test_c_defined_int():
    assert c_defined_int('X', add_source='#define X 3') == 3

def test_rfficache():
    cache = RffiCache(udir.join('cache.py'))
    assert cache.inttype('uchar', 'unsigned char', False)._type.BITS == 8
    assert cache.inttype('uchar', 'unsigned char', False, compiler_exe='xxx')._type.BITS == 8
    assert cache.defined('STUFF', add_source='#define STUFF')
    assert cache.defined('STUFF')
    assert cache.intdefined('STUFFI', add_source='#define STUFFI 3') == 3
    assert cache.intdefined('STUFFI') == 3
    assert cache.sizeof('short') == 2
    cache = RffiCache(udir.join('cache.py'))
    assert cache.intdefined('STUFFI') == 3
    assert cache.defined('STUFF')
    assert cache.inttype('uchar', 'unsigned char', False, compiler_exe='xxx')._type.BITS == 8
    assert cache.sizeof('short', compiler_exe='xxx') == 2

def test_types_present():
    for name in rffi.TYPES:
        if name.startswith('unsigned'):
            name = 'u' + name[9:]
        name = name.replace(' ', '')
        assert hasattr(rffi, 'r_' + name)
        assert hasattr(rffi, name.upper())
