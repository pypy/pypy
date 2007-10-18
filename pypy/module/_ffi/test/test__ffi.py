

from pypy.conftest import gettestobjspace
from pypy.translator.tool.cbuild import compile_c_module

import os, sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestCTypes:
    def prepare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.join("xlib.c")
        c_file.write(py.code.Source('''
        #include <stdlib.h>
        #include <stdio.h>

        struct x
        {
           int x1;
           short x2;
           char x3;
           struct x* next;
        };

        void nothing()
        {
        }

        char inner_struct_elem(struct x *x1)
        {
           return x1->next->x3;
        }

        struct x* create_double_struct()
        {
           struct x* x1, *x2;

           x1 = (struct x*)malloc(sizeof(struct x));
           x2 = (struct x*)malloc(sizeof(struct x));
           x1->next = x2;
           x2->x2 = 3;
           return x1;
        }
        
        const char *static_str = "xxxxxx";
        
        unsigned short add_shorts(short one, short two)
        {
           return one + two;
        }

        char get_char(char* s, unsigned short num)
        {
           return s[num];
        }

        char *char_check(char x, char y)
        {
           if (y == static_str[0])
              return static_str;
           return NULL;
        }

        int get_array_elem(int* stuff, int num)
        {
           return stuff[num];
        }

        struct x* get_array_elem_s(struct x** array, int num)
        {
           return array[num];
        }

        long long some_huge_value()
        {
           return 1LL<<42;
        }

        unsigned long long some_huge_uvalue()
        {
           return 1LL<<42;
        }
        '''))
        compile_c_module([c_file], 'x')
        return str(udir.join('x.so'))
    prepare_c_example = staticmethod(prepare_c_example)
    
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ffi','struct'))
        cls.space = space
        cls.w_lib_name = space.wrap(cls.prepare_c_example())

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

    def test_getchar(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        get_char = lib.ptr('get_char', ['s', 'H'], 'c')
        assert get_char('dupa', 2) == 'p'
        assert get_char('dupa', 1) == 'u'
        raises(ValueError, "get_char('xxx', 2 ** 17)")
        raises(ValueError, "get_char('xxx', -1)")

    def test_returning_str(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        char_check = lib.ptr('char_check', ['c', 'c'], 's')
        assert char_check('y', 'x') == 'xxxxxx'
        assert char_check('x', 'y') is None

    def test_short_addition(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        short_add = lib.ptr('add_shorts', ['h', 'h'], 'H')
        assert short_add(1, 2) == 3

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

    def test_nested_structures(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        inner = lib.ptr("inner_struct_elem", ['P'], 'c')
        X = _ffi.Structure([('x1', 'i'), ('x2', 'h'), ('x3', 'c'), ('next', 'P')])
        x = X(next=X(next=None, x3='x'), x1=1, x2=2, x3='x')
        assert X(x.next).x3 == 'x'
        assert inner(x) == 'x'
        create_double_struct = lib.ptr("create_double_struct", [], 'P')
        x = create_double_struct()
        assert X(X(x).next).x2 == 3

    def test_array(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        A = _ffi.Array('i')
        get_array_elem = lib.ptr('get_array_elem', ['P', 'i'], 'i')
        a = A(10)
        a[8] = 3
        a[7] = 1
        a[6] = 2
        assert get_array_elem(a, 9) == 0
        assert get_array_elem(a, 8) == 3
        assert get_array_elem(a, 7) == 1
        assert get_array_elem(a, 6) == 2
        assert a[3] == 0

    def test_array_of_structure(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        A = _ffi.Array('P')
        X = _ffi.Structure([('x1', 'i'), ('x2', 'h'), ('x3', 'c'), ('next', 'P')])
        x = X(x2=3)
        a = A(3)
        a[1] = x
        get_array_elem_s = lib.ptr('get_array_elem_s', ['P', 'i'], 'P')
        ptr1 = get_array_elem_s(a, 0)
        assert ptr1 is None
        assert X(get_array_elem_s(a, 1)).x2 == 3

    def test_bad_parameters(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        nothing = lib.ptr('nothing', [], None)
        assert nothing() is None
        raises(AttributeError, "lib.ptr('get_charx', [], None)")
        raises(ValueError, "lib.ptr('get_char', ['xx'], None)")
        raises(ValueError, "lib.ptr('get_char', ['x'], None)")
        raises(ValueError, "lib.ptr('get_char', [], 'x')")
        raises(ValueError, "_ffi.Structure(['x1', 'xx'])")
        S = _ffi.Structure([('x1', 'i')])
        S.fields[0] = ('x1', 'xx')
        raises(ValueError, "S()")
        raises(ValueError, "_ffi.Array('xx')")
        A = _ffi.Array('i')
        A.of = 'xx'
        raises(ValueError, 'A(1)')

    def test_implicit_structure(self):
        skip("Does not work yet")
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        X = _ffi.Structure([('x1', 'i'), ('x2', 'h'), ('x3', 'c'), ('next', 'self')])
        inner = lib.ptr("inner_struct_elem", [X], 'c')
        x = X(next=X(next=None, x3='x'), x1=1, x2=2, x3='x')
        assert x.next.x3 == 'x'
        assert inner(x) == 'x'
        create_double_struct = lib.ptr("create_double_struct", [], X)
        x = create_double_struct()
        assert x.next.x2 == 3
        

    def test_longs_ulongs(self):
        import _ffi
        lib = _ffi.CDLL(self.lib_name)
        some_huge_value = lib.ptr('some_huge_value', [], 'q')
        assert some_huge_value() == 1<<42
        some_huge_uvalue = lib.ptr('some_huge_uvalue', [], 'Q')
        assert some_huge_uvalue() == 1<<42
        x = lib.ptr('some_huge_value', ['Q'], None)
        raises(ValueError, "x(-1)")
