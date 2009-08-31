import py, sys, struct
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rffi
from pypy.tool.udir import udir
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform

def import_ctypes():
    try:
        import ctypes
    except ImportError:
        py.test.skip("this test requires ctypes")
    return ctypes

def test_dirent():
    dirent = rffi_platform.getstruct("struct dirent",
                                       """
           struct dirent  /* for this example only, not the exact dirent */
           {
               long d_ino;
               int d_off;
               unsigned short d_reclen;
               char d_name[32];
           };
                                       """,
                                       [("d_reclen", rffi.USHORT)])
    
    assert isinstance(dirent, lltype.Struct)
    # check that we have the desired field
    assert dirent.c_d_reclen is rffi.USHORT

    ctypes = import_ctypes()
    class CTypesDirent(ctypes.Structure):
        _fields_ = [('d_ino', ctypes.c_long),
                    ('d_off', ctypes.c_int),
                    ('d_reclen', ctypes.c_ushort),
                    ('d_name', ctypes.c_char * 32)]

    assert dirent._hints['size'] == ctypes.sizeof(CTypesDirent)

def test_fit_type():
    S = rffi_platform.getstruct("struct S",
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
               double d;
           };
                                  """,
                                  [("c",   rffi.INT),
                                   ("uc",  rffi.INT),
                                   ("s",   rffi.UINT),
                                   ("us",  rffi.INT),
                                   ("i",   rffi.INT),
                                   ("ui",  rffi.INT),
                                   ("l",   rffi.INT),
                                   ("ul",  rffi.INT),
                                   ("ll",  rffi.INT),
                                   ("ull", rffi.INT),
                                   ("d",   rffi.DOUBLE)])
    # XXX we need to have a float here as well as soon as we'll
    #     have support
    assert isinstance(S, lltype.Struct)
    assert S.c_c == rffi.SIGNEDCHAR
    assert S.c_uc == rffi.UCHAR
    assert S.c_s == rffi.SHORT
    assert S.c_us == rffi.USHORT
    assert S.c_i == rffi.INT
    assert S.c_ui == rffi.UINT
    assert S.c_l == rffi.LONG
    assert S.c_ul == rffi.ULONG
    assert S.c_ll == rffi.LONGLONG
    assert S.c_ull == rffi.ULONGLONG
    assert S.c_d == rffi.DOUBLE

def test_simple_type():
    ctype = rffi_platform.getsimpletype('test_t',
                                        'typedef unsigned short test_t;',
                                        rffi.INT)
    assert ctype == rffi.USHORT

def test_constant_integer():
    value = rffi_platform.getconstantinteger('BLAH',
                                               '#define BLAH (6*7)')
    assert value == 42
    value = rffi_platform.getconstantinteger('BLAH',
                                               '#define BLAH (-2147483648LL)')
    assert value == -2147483648
    value = rffi_platform.getconstantinteger('BLAH',
                                               '#define BLAH (3333333333ULL)')
    assert value == 3333333333

def test_defined():
    res = rffi_platform.getdefined('ALFKJLKJFLKJFKLEJDLKEWMECEE', '')
    assert not res
    res = rffi_platform.getdefined('ALFKJLKJFLKJFKLEJDLKEWMECEE',
                                     '#define ALFKJLKJFLKJFKLEJDLKEWMECEE')
    assert res

def test_configure():
    test_h = udir.join('test_ctypes_platform.h')
    test_h.write('#define XYZZY 42\n')

    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            pre_include_bits = ["/* a C comment */",
                                "#include <stdio.h>",
                                "#include <test_ctypes_platform.h>"],
            include_dirs = [str(udir)]
        )

        FILE = rffi_platform.Struct('FILE', [])
        ushort = rffi_platform.SimpleType('unsigned short')
        XYZZY = rffi_platform.ConstantInteger('XYZZY')

    res = rffi_platform.configure(CConfig)
    assert isinstance(res['FILE'], lltype.Struct)
    assert res == {'FILE': res['FILE'],
                   'ushort': rffi.USHORT,
                   'XYZZY': 42}

def test_ifdef():
    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            post_include_bits = ['/* a C comment */',
                                 '#define XYZZY 42',
                                 'typedef int foo;',
                                 '''
                                 struct s {
                                   int i;
                                   double f;
                                 };
                                 '''])

        s = rffi_platform.Struct('struct s', [('i', rffi.INT)],
                                   ifdef='XYZZY')
        z = rffi_platform.Struct('struct z', [('i', rffi.INT)],
                                   ifdef='FOOBAR')

        foo = rffi_platform.SimpleType('foo', ifdef='XYZZY')
        bar = rffi_platform.SimpleType('bar', ifdef='FOOBAR')

    res = rffi_platform.configure(CConfig)
    assert res['s'] is not None
    assert res['z'] is None
    assert res['foo'] is not None
    assert res['bar'] is None

def test_nested_structs():
    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            post_include_bits=["""
            struct x {
            int foo;
            unsigned long bar;
            };
            struct y {
            char c;
            struct x x;
            };
            """])
        x = rffi_platform.Struct("struct x", [("bar", rffi.SHORT)])
        y = rffi_platform.Struct("struct y", [("x", x)])

    res = rffi_platform.configure(CConfig)
    c_x = res["x"]
    c_y = res["y"]
    assert isinstance(c_x, lltype.Struct)
    assert isinstance(c_y, lltype.Struct)
    assert c_y.c_x is c_x

def test_nested_structs_in_the_opposite_order():
    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            post_include_bits=["""
            struct y {
            int foo;
            unsigned long bar;
            };
            struct x {
            char c;
            struct y y;
            };
            """])
        y = rffi_platform.Struct("struct y", [("bar", rffi.SHORT)])
        x = rffi_platform.Struct("struct x", [("y", y)])

    res = rffi_platform.configure(CConfig)
    c_x = res["x"]
    c_y = res["y"]
    assert isinstance(c_x, lltype.Struct)
    assert isinstance(c_y, lltype.Struct)
    assert c_x.c_y is c_y

def test_array():
    dirent = rffi_platform.getstruct("struct dirent",
                                       """
           struct dirent  /* for this example only, not the exact dirent */
           {
               long d_ino;
               int d_off;
               unsigned short d_reclen;
               char d_name[32];
           };
                                       """,
                                       [("d_name", lltype.FixedSizeArray(rffi.CHAR, 1))])
    assert dirent.c_d_name.length == 32

def test_has():
    assert rffi_platform.has("x", "int x = 3;")
    assert not rffi_platform.has("x", "")
    # has() should also not crash if it is given an invalid #include
    assert not rffi_platform.has("x", "#include <some/path/which/cannot/exist>")

def test_verify_eci():
    eci = ExternalCompilationInfo()
    rffi_platform.verify_eci(eci)
    eci = ExternalCompilationInfo(libraries=['some_name_that_doesnt_exist_'])
    py.test.raises(rffi_platform.CompilationError,
                   rffi_platform.verify_eci, eci)

def test_sizeof():
    assert rffi_platform.sizeof("char", ExternalCompilationInfo()) == 1

def test_memory_alignment():
    a = rffi_platform.memory_alignment()
    print a
    assert a % struct.calcsize("P") == 0

def test_external_lib():
    # XXX this one seems to be a bit too platform-specific. Check
    #     how to test it on windows correctly (using so_prefix?)
    #     and what are alternatives to LD_LIBRARY_PATH
    eci = ExternalCompilationInfo()
    c_source = """
    int f(int a, int b)
    {
        return (a + b);
    }
    """
    tmpdir = udir.join('external_lib').ensure(dir=1)
    c_file = tmpdir.join('libc_lib.c')
    c_file.write(c_source)
    l = platform.compile([c_file], eci, standalone=False)
    eci = ExternalCompilationInfo(
        libraries = ['c_lib'],
        library_dirs = [str(tmpdir)]
        )
    rffi_platform.verify_eci(eci)
