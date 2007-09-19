
import py
from pypy.rpython.lltypesystem.rffi import *
from pypy.translator.c.test.test_genc import compile
from pypy.rpython.lltypesystem.lltype import Signed, Ptr, Char, malloc
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir
from pypy.rpython.test.test_llinterp import interpret, MallocMismatch
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.rtyper import RPythonTyper
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.translator import graphof
from pypy.conftest import option
from pypy.objspace.flow.model import summary

def test_basic():
    c_source = py.code.Source("""
    int z(int x)
    {
        return (x + 3);
    }
    """)
    z = llexternal('z', [Signed], Signed, sources=[c_source])

    def f():
        return z(8)

    xf = compile(f, [])
    assert xf() == 8+3

def test_hashdefine():
    c_source = """
    #define X(i) (i+3)
    """

    c_file = udir.join("stuff.c")
    c_file.write(c_source)

    z = llexternal('X', [Signed], Signed, includes=[str(c_file)])

    def f():
        return z(8)

    xf = compile(f, [])
    assert xf() == 8+3

def test_string():
    z = llexternal('strlen', [CCHARP], Signed, includes=['string.h'],
                   stringpolicy='noauto')

    def f():
        s = str2charp("xxx")
        res = z(s)
        free_charp(s)
        return res

    xf = compile(f, [], backendopt=False)
    assert xf() == 3

def test_string_reverse():
    c_source = py.code.Source("""
    #include <string.h>

    char *f(char* arg)
    {
        char *ret;
        ret = (char*)malloc(strlen(arg) + 1);
        strcpy(ret, arg);
        return ret;
    }
    """)
    z = llexternal('f', [CCHARP], CCHARP, sources=[c_source],
                   stringpolicy='noauto')

    def f():
        s = str2charp("xxx")
        l_res = z(s)
        res = charp2str(l_res)
        lltype.free(l_res, flavor='raw')
        free_charp(s)
        return len(res)

    xf = compile(f, [], backendopt=False)
    assert xf(expected_extra_mallocs=-1) == 3

def test_stringstar():
    c_source = """
    #include <string.h>
    
    int f(char *args[]) {
        char **p = args;
        int l = 0;
        while (*p) {
            l += strlen(*p);
            p++;
        }
        return (l);
    }
    """
    z = llexternal('f', [CCHARPP], Signed, sources=[c_source])

    def f():
        l = ["xxx", "x", "xxxx"]
        ss = liststr2charpp(l)
        result = z(ss)
        free_charpp(ss)
        return result

    xf = compile(f, [], backendopt=False)
    assert xf() == 8

def test_struct():
    h_source = """
    struct xx {
       int one;
       char two;
       int three;
    };
    """
    h_file = udir.join("structxx.h")
    h_file.write(h_source)
    
    c_source = """
    int f(struct xx* z)
    {
      return (z->one + z->three);
    }
    """
    TP = CStructPtr('xx', ('one', Signed), ('two', Char), ('three', Signed))

    z = llexternal('f', [TP], Signed, sources=[c_source],
                   includes=[str(h_file)], include_dirs=[udir])

    def f():
        struct = lltype.malloc(TP.TO, flavor='raw')
        struct.c_one = 3
        struct.c_two = '\x33'
        struct.c_three = 5
        result = z(struct)
        lltype.free(struct, flavor='raw')
        return result

    fn = compile(f, [], backendopt=False)
    assert fn() == 8

def test_externvar():
    import os

    def f():
        set_errno(12)
        return get_errno()

    def g():
        try:
            os.write(12312312, "xxx")
        except OSError:
            pass
        return get_errno()

    fn = compile(f, [])
    assert fn() == 12
    gn = compile(g, [])
    import errno
    assert gn() == errno.EBADF

def test_external_callable():
    """ Try to call some llexternal function with llinterp
    """
    z = llexternal('z', [Signed], Signed, _callable=lambda x:x+1)
    
    def f():
        return z(2)

    res = interpret(f, [])
    assert res == 3

def test_extra_include_dirs():
    udir.ensure("incl", dir=True)
    udir.join("incl", "incl.h").write("#define C 3")
    c_source = py.code.Source("""
    #include <incl.h>
    int fun ()
    {
        return (C);
    }
    """)
    z = llexternal('fun', [], Signed, sources=[c_source], include_dirs=
                   [str(udir.join("incl"))])

    def f():
        return z()

    res = compile(f, [])
    assert res() == 3

def test_size_t_sign():
    assert r_size_t(-1) > 0

def test_cast():
    res = cast(SIZE_T, -1)
    assert type(res) is r_size_t
    assert res == r_size_t(-1)

def test_compile_cast():
    def f(n):
        return cast(SIZE_T, n)

    f1 = compile(f, [int])
    res = f1(-1)
    assert res == r_size_t(-1)

def test_opaque_type():
    h_source = py.code.Source("""
    struct stuff {
       char data[38];
    };

    char get(struct stuff* x)
    {
       x->data[13] = 'a';
       return x->data[13];
    }
    """)
    # if it doesn't segfault, than we probably malloced it :-)
    h_file = udir.join("opaque.h")
    h_file.write(h_source)

    STUFFP = COpaquePtr('struct stuff', includes=['opaque.h'],
                     include_dirs=[str(udir)])

    ll_get = llexternal('get', [STUFFP], lltype.Char, includes=['opaque.h'],
                        include_dirs=[str(udir)])

    def f():
        ll_stuff = lltype.malloc(STUFFP.TO, flavor='raw')
        result = ll_get(ll_stuff)
        lltype.free(ll_stuff, flavor='raw')
        return result

    f1 = compile(f, [])
    assert f1() == 'a'

def test_rffi_sizeof():
    try:
        import ctypes
    except ImportError:
        py.test.skip("Cannot test without ctypes")
    cache = {
        lltype.Signed:   ctypes.c_long,
        lltype.Unsigned: ctypes.c_ulong,
        lltype.Char:     ctypes.c_ubyte,
        DOUBLE:     ctypes.c_double,
        SIGNEDCHAR: ctypes.c_byte,
        UCHAR:      ctypes.c_ubyte,
        SHORT:      ctypes.c_short,
        USHORT:     ctypes.c_ushort,
        INT:        ctypes.c_int,
        UINT:       ctypes.c_uint,
        LONG:       ctypes.c_long,
        ULONG:      ctypes.c_ulong,
        LONGLONG:   ctypes.c_longlong,
        ULONGLONG:  ctypes.c_ulonglong,
        SIZE_T:     ctypes.c_size_t,
        }

    for ll, ctp in cache.items():
        assert sizeof(ll) == ctypes.sizeof(ctp)
    assert not size_and_sign(lltype.Signed)[1]
    assert not size_and_sign(lltype.Char)[1]
    assert size_and_sign(UINT)[1]

def test_rffi_offsetof():
    import struct
    from pypy.rpython.tool import rffi_platform
    S = rffi_platform.getstruct("struct S",
                                  """
           struct S {
               short a;
               int b, c;
           };                     """,
                                  [("a", INT),
                                   ("b", INT),
                                   ("c", INT)])
    assert sizeof(S) == struct.calcsize("hii")
    assert offsetof(S, "c_a") == 0
    assert offsetof(S, "c_b") == struct.calcsize("hi") - struct.calcsize("i")
    assert offsetof(S, "c_c") == struct.calcsize("hii") - struct.calcsize("i")

def test_prebuild_constant():
    py.test.skip("WIP")
    h_source = py.code.Source("""
    #ifndef _CONSTANTS
    #define _CONSTANTS
    int x = 3;
    char** z = NULL;
    #endif
    """)
    h_include = udir.join('constants.h')
    h_include.write(h_source)

    kwds = {'includes':['constants.h'], 'include_dirs':[str(udir)]}
    get_x, set_x = CExternVariable(lltype.Signed, 'x', **kwds)
    get_z, set_z = CExternVariable(CCHARPP, 'z', **kwds)

    def f():
        one = get_x()
        set_x(13)
        return one + get_x()

    def g():
        l = liststr2charpp(["a", "b", "c"])
        try:
            set_z(l)
            return charp2str(get_z()[2])
        finally:
            free_charpp(l)

    fn = compile(f, [])
    assert fn() == 16
    gn = compile(g, [])
    assert gn() == "c"
    
def test_struct_create():
    X = CStruct('xx', ('one', INT))
    def f():
        p = make(X, c_one=3)
        res = p.c_one
        lltype.free(p, flavor='raw')
        return res
    assert f() == 3
    assert interpret(f, []) == 3

def test_structcopy():
    X2 = lltype.Struct('X2', ('x', INT))
    X1 = lltype.Struct('X1', ('a', INT), ('x2', X2), ('p', lltype.Ptr(X2)))
    def f():
        p2 = make(X2, x=123)
        p1 = make(X1, a=5, p=p2)
        p1.x2.x = 456
        p1bis = make(X1)
        p2bis = make(X2)
        structcopy(p1bis, p1)
        assert p1bis.a == 5
        assert p1bis.x2.x == 456
        assert p1bis.p == p2
        structcopy(p2bis, p2)
        res = p2bis.x
        lltype.free(p2bis, flavor='raw')
        lltype.free(p1bis, flavor='raw')
        lltype.free(p2, flavor='raw')
        lltype.free(p1, flavor='raw')
        return res
    assert f() == 123
    res = interpret(f, [])
    assert res == 123

def test_implicit_cast():
    z = llexternal('z', [USHORT, ULONG, USHORT, DOUBLE], USHORT)

    def f(x, y, xx, yy):
        return z(x, y, xx, yy)

    a = RPythonAnnotator()
    r = a.build_types(f, [int, int, int, int])
    rtyper = RPythonTyper(a)
    rtyper.specialize()
    a.translator.rtyper = rtyper
    backend_optimizations(a.translator)
    if option.view:
        a.translator.view()
    graph = graphof(a.translator, f)
    s = summary(graph)
    # there should be not too many operations here by now
    assert s == {'cast_int_to_uint': 1, 'direct_call': 1, 'cast_primitive': 2,
                 'cast_int_to_float': 1}
    

def test_stringpolicy1():
    strlen = llexternal('strlen', [CCHARP], INT, includes=['string.h'],
                        stringpolicy='fullauto')
    def f():
        return strlen("Xxx")
    assert interpret(f, [], backendopt=True) == 3

def test_stringpolicy2():
    def f():
        return strlen("Xxx")        
    strlen = llexternal('strlen', [CCHARP], INT,
                        includes=['string.h'], stringpolicy='autocast')
    py.test.raises(MallocMismatch, interpret, f, [], backendopt=True)

def test_stringpolicy3():
    strlen = llexternal('strlen', [CCHARP], INT,
                        includes=['string.h'], stringpolicy='noauto')
    def f():
        ll_str = str2charp("Xxx")
        res = strlen(ll_str)
        lltype.free(ll_str, flavor='raw')
        return res

    assert interpret(f, [], backendopt=True) == 3
    
def test_around_extcall():
    import os
    from pypy.annotation import model as annmodel
    from pypy.rlib.objectmodel import invoke_around_extcall
    from pypy.rpython.extfuncregistry import register_external
    read_fd, write_fd = os.pipe()
    try:
        # we need an external function that is not going to get wrapped around
        # before()/after() calls, in order to call it from before()/after()...
        def mywrite(s):
            os.write(write_fd, s)
        def llimpl(s):
            s = ''.join(s.chars)
            os.write(write_fd, s)
        register_external(mywrite, [str], annmodel.s_None, 'll_mywrite',
                          llfakeimpl=llimpl, sandboxsafe=True)

        def before():
            mywrite("B")
        def after():
            mywrite("A")
        def f():
            os.write(write_fd, "-")
            invoke_around_extcall(before, after)
            os.write(write_fd, "E")

        interpret(f, [])
        data = os.read(read_fd, 99)
        assert data == "-BEA"

    finally:
        os.close(write_fd)
        os.close(read_fd)
