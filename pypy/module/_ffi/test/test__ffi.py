

from pypy.conftest import gettestobjspace

import os, sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestCTypes:
    def prepare_c_example():
        from pypy.tool.udir import udir
        udir.join("xlib.c").write(py.code.Source("""
        typedef struct x {
           char x1;
           long x2;
           struct x *x3;
        }
        """))
    prepare_c_example = staticmethod(prepare_c_example)
    
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_ffi','struct'))
        cls.prepare_c_example()

    def test_libload(self):
        import _ffi
        _ffi.CDLL('libc.so.6')

    def test_getattr(self):
        import _ffi
        libc = _ffi.CDLL('libc.so.6')
        func = libc.ptr('rand', [], 'i')
        assert libc.ptr('rand', [], 'i') is func # caching
        assert libc.ptr('rand', [], 'l') is not func
        assert isinstance(func, _ffi.FuncPtr)
        raises(AttributeError, "libc.xxxxxxxxxxxxxx")

    def test_rand(self):
        import _ffi
        libc = _ffi.CDLL('libc.so.6')
        func = libc.ptr('rand', [], 'i')
        first = func()
        count = 0
        for i in range(100):
            res = func()
            if res == first:
                count += 1
        assert count != 100

    def test_pow(self):
        import _ffi
        libm = _ffi.CDLL('libm.so')
        pow = libm.ptr('pow', ['d', 'd'], 'd')
        assert pow(2.0, 2.0) == 4.0
        assert pow(3.0, 3.0) == 27.0
        assert pow(2, 2) == 4.0
        raises(TypeError, "pow('x', 2.0)")

    def test_strlen(self):
        import _ffi
        libc = _ffi.CDLL('libc.so.6')
        strlen = libc.ptr('strlen', ['s'], 'i')
        assert strlen("dupa") == 4
        assert strlen("zupa") == 4
        strlen = libc.ptr('strlen', ['P'], 'i')
        assert strlen("ddd\x00") == 3
        strdup = libc.ptr('strdup', ['s'], 's')
        assert strdup("xxx") == "xxx"

    def test_time(self):
        import _ffi
        libc = _ffi.CDLL('libc.so.6')
        time = libc.ptr('time', ['P'], 'l')
        assert time(None) != 0

    def test_gettimeofday(self):
        import _ffi
        struct_type = _ffi.Structure([('tv_sec', 'l'), ('tv_usec', 'l')])
        structure = struct_type()
        libc = _ffi.CDLL('libc.so.6')
        gettimeofday = libc.ptr('gettimeofday', ['P', 'P'], 'i')
        assert gettimeofday(structure, None) == 0
        struct2 = struct_type()
        assert gettimeofday(struct2, None) == 0
        assert structure.tv_usec != struct2.tv_usec
        assert (structure.tv_sec == struct2.tv_sec) or (structure.tv_sec == struct2.tv_sec - 1)
        raises(AttributeError, "structure.xxx")

    def test_structreturn(self):
        import _ffi
        X = _ffi.Structure([('x', 'l')])
        x = X()
        x.x = 121
        Tm = _ffi.Structure([('tm_sec', 'i'),
                             ('tm_min', 'i'),
                             ('tm_hour', 'i'),
                             ("tm_mday", 'i'),
                             ("tm_mon", 'i'),
                             ("tm_year", 'i'),
                             ("tm_wday", 'i'),
                             ("tm_yday", 'i'),
                             ("tm_isdst", 'i')])
        libc = _ffi.CDLL('libc.so.6')
        gmtime = libc.ptr('gmtime', ['P'], 'P')
        t = Tm(gmtime(x))
        assert t.tm_year == 70
        assert t.tm_sec == 1
        assert t.tm_min == 2
        

    #def test_nested_structures(self):
    #    
