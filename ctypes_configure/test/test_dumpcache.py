import ctypes
from ctypes_configure import configure, dumpcache
from ctypes_configure.cbuild import ExternalCompilationInfo


def test_cache():
    configdir = configure.configdir
    test_h = configdir.join('test_ctypes_platform2.h')
    test_h.write('#define XYZZY 42\n'
                 "#define large 2147483648L\n")

    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            pre_include_lines = ["/* a C comment */",
                                 "#include <stdio.h>",
                                 "#include <test_ctypes_platform2.h>"],
            include_dirs = [str(configdir)]
        )

        FILE = configure.Struct('FILE', [])
        ushort = configure.SimpleType('unsigned short')
        XYZZY = configure.ConstantInteger('XYZZY')
        XUZ = configure.Has('XUZ')
        large = configure.DefinedConstantInteger('large')
        undef = configure.Defined('really_undefined')

    res = configure.configure(CConfig)

    cachefile = configdir.join('cache')
    dumpcache.dumpcache('', str(cachefile), res)

    d = {}
    execfile(str(cachefile), d)
    assert d['XYZZY'] == res['XYZZY']
    assert d['ushort'] == res['ushort']
    assert d['FILE']._fields_ == res['FILE']._fields_
    assert d['FILE'].__mro__[1:] == res['FILE'].__mro__[1:]
    assert d['undef'] == res['undef']
    assert d['large'] == res['large']
    assert d['XUZ'] == res['XUZ']


def test_cache_array():
    configdir = configure.configdir
    res = {'foo': ctypes.c_short * 27}
    cachefile = configdir.join('cache_array')
    dumpcache.dumpcache('', str(cachefile), res)
    #
    d = {}
    execfile(str(cachefile), d)
    assert d['foo'] == res['foo']

def test_cache_array_array():
    configdir = configure.configdir
    res = {'foo': (ctypes.c_int * 2) * 3}
    cachefile = configdir.join('cache_array_array')
    dumpcache.dumpcache('', str(cachefile), res)
    #
    d = {}
    execfile(str(cachefile), d)
    assert d['foo'] == res['foo']
