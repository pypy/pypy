import py, sys, struct
from ctypes_configure import configure
from ctypes_configure.cbuild import ExternalCompilationInfo
import ctypes

def test_dirent():
    dirent = configure.getstruct("struct dirent",
                                       """
           struct dirent  /* for this example only, not the exact dirent */
           {
               long d_ino;
               int d_off;
               unsigned short d_reclen;
               char d_name[32];
           };
                                       """,
                                       [("d_reclen", ctypes.c_ushort)])
    assert issubclass(dirent, ctypes.Structure)
    ssize = (ctypes.sizeof(ctypes.c_long) +
             ctypes.sizeof(ctypes.c_int) +
             ctypes.sizeof(ctypes.c_ushort) +
             32)
    extra_padding = (-ssize) % ctypes.alignment(ctypes.c_long)

    assert dirent._fields_ == [('_alignment', ctypes.c_long),
                               ('_pad0', ctypes.c_char),
                               ('_pad1', ctypes.c_char),
                               ('_pad2', ctypes.c_char),
                               ('_pad3', ctypes.c_char),
                               ('d_reclen', ctypes.c_ushort),
                               ] + [
                               ('_pad%d' % n, ctypes.c_char)
                                    for n in range(4, 4+32+extra_padding)]
    assert ctypes.sizeof(dirent) == ssize + extra_padding
    assert ctypes.alignment(dirent) == ctypes.alignment(ctypes.c_long)

def test_fit_type():
    S = configure.getstruct("struct S",
                                  """
           struct S {
               signed char c;
               unsigned char uc;
               short s;
               unsigned short us;
               int i;
               unsigned int ui;
               long l;
               unsigned long ul;
               long long ll;
               unsigned long long ull;
               float f;
               double d;
           };
                                  """,
                                  [("c",   ctypes.c_int),
                                   ("uc",  ctypes.c_int),
                                   ("s",   ctypes.c_uint),
                                   ("us",  ctypes.c_int),
                                   ("i",   ctypes.c_int),
                                   ("ui",  ctypes.c_int),
                                   ("l",   ctypes.c_int),
                                   ("ul",  ctypes.c_int),
                                   ("ll",  ctypes.c_int),
                                   ("ull", ctypes.c_int),
                                   ("f",   ctypes.c_double),
                                   ("d",   ctypes.c_float)])
    assert issubclass(S, ctypes.Structure)
    fields = dict(S._fields_)
    assert fields["c"] == ctypes.c_byte
    assert fields["uc"] == ctypes.c_ubyte
    assert fields["s"] == ctypes.c_short
    assert fields["us"] == ctypes.c_ushort
    assert fields["i"] == ctypes.c_int
    assert fields["ui"] == ctypes.c_uint
    assert fields["l"] == ctypes.c_long
    assert fields["ul"] == ctypes.c_ulong
    assert fields["ll"] == ctypes.c_longlong
    assert fields["ull"] == ctypes.c_ulonglong
    assert fields["f"] == ctypes.c_float
    assert fields["d"] == ctypes.c_double

def test_simple_type():
    ctype = configure.getsimpletype('test_t',
                                          'typedef unsigned short test_t;',
                                          ctypes.c_int)
    assert ctype == ctypes.c_ushort

def test_constant_integer():
    value = configure.getconstantinteger('BLAH',
                                               '#define BLAH (6*7)')
    assert value == 42
    value = configure.getconstantinteger('BLAH',
                                               '#define BLAH (-2147483648LL)')
    assert value == -2147483648
    value = configure.getconstantinteger('BLAH',
                                               '#define BLAH (3333333333ULL)')
    assert value == 3333333333

def test_defined():
    res = configure.getdefined('ALFKJLKJFLKJFKLEJDLKEWMECEE', '')
    assert not res
    res = configure.getdefined('ALFKJLKJFLKJFKLEJDLKEWMECEE',
                                     '#define ALFKJLKJFLKJFKLEJDLKEWMECEE')
    assert res

def test_configure():
    configdir = configure.configdir
    test_h = configdir.join('test_ctypes_platform.h')
    test_h.write('#define XYZZY 42\n')

    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            pre_include_lines = ["/* a C comment */",
                                 "#include <stdio.h>",
                                 "#include <test_ctypes_platform.h>"],
            include_dirs = [str(configdir)]
        )

        FILE = configure.Struct('FILE', [])
        ushort = configure.SimpleType('unsigned short')
        XYZZY = configure.ConstantInteger('XYZZY')

    res = configure.configure(CConfig)
    assert issubclass(res['FILE'], ctypes.Structure)
    assert res == {'FILE': res['FILE'],
                   'ushort': ctypes.c_ushort,
                   'XYZZY': 42}

def test_ifdef():
    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            post_include_lines = ['/* a C comment */',
                                  '#define XYZZY 42',
                                  'typedef int foo;',
                                  'struct s {',
                                  'int i;',
                                  'double f;'
                                  '};'])


        s = configure.Struct('struct s', [('i', ctypes.c_int)],
                                   ifdef='XYZZY')
        z = configure.Struct('struct z', [('i', ctypes.c_int)],
                                   ifdef='FOOBAR')

        foo = configure.SimpleType('foo', ifdef='XYZZY')
        bar = configure.SimpleType('bar', ifdef='FOOBAR')

    res = configure.configure(CConfig)
    assert res['s'] is not None
    assert res['z'] is None
    assert res['foo'] is not None
    assert res['bar'] is None

def test_nested_structs():
    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            post_include_lines="""
            struct x {
            int foo;
            unsigned long bar;
            };
            struct y {
            char c;
            struct x x;
            };
            """.split("\n"))

        x = configure.Struct("struct x", [("bar", ctypes.c_short)])
        y = configure.Struct("struct y", [("x", x)])

    res = configure.configure(CConfig)
    c_x = res["x"]
    c_y = res["y"]
    c_y_fields = dict(c_y._fields_)
    assert issubclass(c_x , ctypes.Structure)
    assert issubclass(c_y, ctypes.Structure)
    assert c_y_fields["x"] is c_x

def test_array():
    dirent = configure.getstruct("struct dirent",
                                       """
           struct dirent  /* for this example only, not the exact dirent */
           {
               long d_ino;
               int d_off;
               unsigned short d_reclen;
               char d_name[32];
           };
                                       """,
                                       [("d_name", ctypes.c_char * 0)])
    assert dirent.d_name.size == 32

def test_has():
    assert configure.has("x", "int x = 3;")
    assert not configure.has("x", "")
    # has() should also not crash if it is given an invalid #include
    assert not configure.has("x", "#include <some/path/which/cannot/exist>")

def test_check_eci():
    eci = ExternalCompilationInfo()
    assert configure.check_eci(eci)
    eci = ExternalCompilationInfo(libraries=['some_name_that_doesnt_exist_'])
    assert not configure.check_eci(eci)

def test_sizeof():
    assert configure.sizeof("char", ExternalCompilationInfo()) == 1

def test_memory_alignment():
    a = configure.memory_alignment()
    print a
    assert a % struct.calcsize("P") == 0
