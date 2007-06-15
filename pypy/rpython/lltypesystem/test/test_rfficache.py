
from pypy.rpython.lltypesystem.rfficache import *
from pypy.rpython.lltypesystem import rffi
from pypy.tool.udir import udir

def test_sizeof_c_type():
    sizeofchar = sizeof_c_type('char')
    assert sizeofchar == 8

def test_gettypesizes():
    tmpfile = udir.join("somecrappyfile.py")
    assert get_type_sizes(tmpfile)['char'] == 8
    # this should not invoke a compiler
    res = get_type_sizes(tmpfile, compiler_exe='xxx')
    assert res['char'] == 8

def test_gettypesizes_platforms():
    tmpfile = udir.join("plat.py")
    tmpfile.write(py.code.Source("""
    platforms = {'xxx':{%s}}
    """ % ", ".join(['"%s":4' % i for i in TYPES])))
    assert get_type_sizes(tmpfile)['char'] == 8
    assert get_type_sizes(tmpfile, platform_key='xxx', compiler_exe='xxx')['char'] == 4

def test_types_present():
    for name in TYPES:
        if name.startswith('unsigned'):
            name = 'u' + name[9:]
        name = name.replace(' ', '')
        assert hasattr(rffi, 'r_' + name)
        assert hasattr(rffi, name.upper())

