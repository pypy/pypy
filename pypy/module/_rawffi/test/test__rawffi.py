

from pypy.conftest import gettestobjspace
from pypy.translator.tool.cbuild import compile_c_module, \
     ExternalCompilationInfo
from pypy.module._rawffi.interp_rawffi import TYPEMAP

import os, sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestFfi:
    def prepare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.ensure("test__rawffi", dir=1).join("xlib.c")
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

        void free_double_struct(struct x* x1)
        {
            free(x1->next);
            free(x1);
        }
        
        const char *static_str = "xxxxxx";
        const long static_int = 42;
        const double static_double = 42.42;
        
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

        long long pass_ll(long long x)
        {
           return x;
        }

        static int prebuilt_array1[] = {3};

        int* allocate_array()
        {
            return prebuilt_array1;
        }

        long long runcallback(long long(*callback)())
        {
            return callback();
        }

        '''))
        return compile_c_module([c_file], 'x', ExternalCompilationInfo())
    prepare_c_example = staticmethod(prepare_c_example)
    
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_rawffi','struct'))
        cls.space = space
        cls.w_lib_name = space.wrap(cls.prepare_c_example())
        cls.w_sizes_and_alignments = space.wrap(dict(
            [(k, (v.c_size, v.c_alignment)) for k,v in TYPEMAP.iteritems()]))

    def test_libload(self):
        import _rawffi
        _rawffi.CDLL('libc.so.6')

    def test_getattr(self):
        import _rawffi
        libc = _rawffi.CDLL('libc.so.6')
        func = libc.ptr('rand', [], 'i')
        assert libc.ptr('rand', [], 'i') is func # caching
        assert libc.ptr('rand', [], 'l') is not func
        assert isinstance(func, _rawffi.FuncPtr)
        raises(AttributeError, "libc.xxxxxxxxxxxxxx")

    def test_getchar(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        get_char = lib.ptr('get_char', ['P', 'H'], 'c')
        A = _rawffi.Array('c')
        B = _rawffi.Array('H')
        dupa = A(5, 'dupa')
        dupaptr = dupa.byptr()
        for i in range(4):
            intptr = B(1)
            intptr[0] = i
            res = get_char(dupaptr, intptr)
            assert res[0] == 'dupa'[i]
            res.free()
            intptr.free()
        dupaptr.free()
        dupa.free()

    def test_returning_str(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        char_check = lib.ptr('char_check', ['c', 'c'], 's')
        A = _rawffi.Array('c')
        arg1 = A(1)
        arg2 = A(1)
        arg1[0] = 'y'
        arg2[0] = 'x'
        res = char_check(arg1, arg2)
        assert _rawffi.charp2string(res[0]) == 'xxxxxx'
        assert _rawffi.charp2rawstring(res[0]) == 'xxxxxx'
        assert _rawffi.charp2rawstring(res[0], 3) == 'xxx'
        a = A(6, 'xx\x00\x00xx')
        assert _rawffi.charp2string(a.buffer) == 'xx'
        assert _rawffi.charp2rawstring(a.buffer, 4) == 'xx\x00\x00'
        res.free()
        arg1[0] = 'x'
        arg2[0] = 'y'
        res = char_check(arg1, arg2)
        assert res[0] == 0
        assert _rawffi.charp2string(res[0]) is None
        res.free()
        arg1.free()
        arg2.free()

    def test_short_addition(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        short_add = lib.ptr('add_shorts', ['h', 'h'], 'H')
        A = _rawffi.Array('h')
        arg1 = A(1)
        arg2 = A(1)
        arg1[0] = 1
        arg2[0] = 2
        res = short_add(arg1, arg2)
        assert res[0] == 3
        res.free()
        arg1.free()
        arg2.free()

    def test_pow(self):
        import _rawffi
        libm = _rawffi.CDLL('libm.so')
        pow = libm.ptr('pow', ['d', 'd'], 'd')
        A = _rawffi.Array('d')
        arg1 = A(1)
        arg2 = A(1)
        raises(TypeError, "arg1[0] = 'x'")
        arg1[0] = 3
        arg2[0] = 2.0
        res = pow(arg1, arg2)
        assert res[0] == 9.0
        res.free()
        arg1.free()
        arg2.free()

    def test_time(self):
        import _rawffi
        libc = _rawffi.CDLL('libc.so.6')
        time = libc.ptr('time', ['z'], 'l')  # 'z' instead of 'P' just for test
        arg = _rawffi.Array('P')(1)
        arg[0] = 0
        res = time(arg)
        assert res[0] != 0
        res.free()
        arg.free()

    def test_gettimeofday(self):
        import _rawffi
        struct_type = _rawffi.Structure([('tv_sec', 'l'), ('tv_usec', 'l')])
        structure = struct_type()
        libc = _rawffi.CDLL('libc.so.6')
        gettimeofday = libc.ptr('gettimeofday', ['P', 'P'], 'i')

        arg1 = structure.byptr()
        arg2 = _rawffi.Array('P')(1)
        res = gettimeofday(arg1, arg2)
        assert res[0] == 0
        res.free()

        struct2 = struct_type()
        arg1[0] = struct2
        res = gettimeofday(arg1, arg2)
        assert res[0] == 0
        res.free()

        assert structure.tv_usec != struct2.tv_usec
        assert (structure.tv_sec == struct2.tv_sec) or (structure.tv_sec == struct2.tv_sec - 1)
        raises(AttributeError, "structure.xxx")
        structure.free()
        struct2.free()
        arg1.free()
        arg2.free()

    def test_structreturn(self):
        import _rawffi
        X = _rawffi.Structure([('x', 'l')])
        x = X()
        x.x = 121
        Tm = _rawffi.Structure([('tm_sec', 'i'),
                                ('tm_min', 'i'),
                                ('tm_hour', 'i'),
                                ("tm_mday", 'i'),
                                ("tm_mon", 'i'),
                                ("tm_year", 'i'),
                                ("tm_wday", 'i'),
                                ("tm_yday", 'i'),
                                ("tm_isdst", 'i')])
        libc = _rawffi.CDLL('libc.so.6')
        gmtime = libc.ptr('gmtime', ['P'], 'P')

        arg = x.byptr()
        res = gmtime(arg)
        t = Tm.fromaddress(res[0])
        res.free()
        arg.free()
        assert t.tm_year == 70
        assert t.tm_sec == 1
        assert t.tm_min == 2      
        x.free()

    def test_nested_structures(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        inner = lib.ptr("inner_struct_elem", ['P'], 'c')
        X = _rawffi.Structure([('x1', 'i'), ('x2', 'h'), ('x3', 'c'), ('next', 'P')])
        next = X(next=0, x3='x')
        x = X(next=next, x1=1, x2=2, x3='x')
        assert X.fromaddress(x.next).x3 == 'x'
        x.free()
        next.free()
        create_double_struct = lib.ptr("create_double_struct", [], 'P')
        res = create_double_struct()
        x = X.fromaddress(res[0])
        assert X.fromaddress(x.next).x2 == 3
        free_double_struct = lib.ptr("free_double_struct", ['P'], None)
        free_double_struct(res)
        res.free()

    def test_array(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        A = _rawffi.Array('i')
        get_array_elem = lib.ptr('get_array_elem', ['P', 'i'], 'i')
        a = A(10)
        a[8] = 3
        a[7] = 1
        a[6] = 2
        arg1 = a.byptr()
        arg2 = A(1)
        for i, expected in enumerate([0, 0, 0, 0, 0, 0, 2, 1, 3, 0]):
            arg2[0] = i
            res = get_array_elem(arg1, arg2)
            assert res[0] == expected
            res.free()
        arg1.free()
        arg2.free()
        assert a[3] == 0
        a.free()

    def test_array_of_structure(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        A = _rawffi.Array('P')
        X = _rawffi.Structure([('x1', 'i'), ('x2', 'h'), ('x3', 'c'), ('next', 'P')])
        x = X(x2=3)
        a = A(3)
        a[1] = x
        get_array_elem_s = lib.ptr('get_array_elem_s', ['P', 'i'], 'P')
        arg1 = a.byptr()
        arg2 = _rawffi.Array('i')(1)
        res = get_array_elem_s(arg1, arg2)
        assert res[0] == 0
        res.free()
        arg2[0] = 1
        res = get_array_elem_s(arg1, arg2)
        assert X.fromaddress(res[0]).x2 == 3
        assert res[0] == x.buffer
        res.free()
        arg1.free()
        arg2.free()
        x.free()
        a.free()

    def test_bad_parameters(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        nothing = lib.ptr('nothing', [], None)
        assert nothing() is None
        raises(AttributeError, "lib.ptr('get_charx', [], None)")
        raises(ValueError, "lib.ptr('get_char', ['xx'], None)")
        raises(ValueError, "lib.ptr('get_char', ['x'], None)")
        raises(ValueError, "lib.ptr('get_char', [], 'x')")
        raises(ValueError, "_rawffi.Structure(['x1', 'xx'])")
        raises(ValueError, _rawffi.Structure, [('x1', 'xx')])
        raises(ValueError, "_rawffi.Array('xx')")

    def test_longs_ulongs(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        some_huge_value = lib.ptr('some_huge_value', [], 'q')
        res = some_huge_value()
        assert res[0] == 1<<42
        res.free()
        some_huge_uvalue = lib.ptr('some_huge_uvalue', [], 'Q')
        res = some_huge_uvalue()
        assert res[0] == 1<<42
        res.free()
        pass_ll = lib.ptr('pass_ll', ['q'], 'q')
        arg1 = _rawffi.Array('q')(1)
        arg1[0] = 1<<42
        res = pass_ll(arg1)
        assert res[0] == 1<<42
        res.free()
        arg1.free()
    
    def test_callback(self):
        import _rawffi
        import struct
        libc = _rawffi.CDLL('libc.so.6')
        ll_to_sort = _rawffi.Array('i')(4)
        for i in range(4):
            ll_to_sort[i] = 4-i
        qsort = libc.ptr('qsort', ['P', 'i', 'i', 'P'], None)
        resarray = _rawffi.Array('i')(1)
        def compare(a, b):
            a1 = _rawffi.Array('i').fromaddress(a, 1)
            a2 = _rawffi.Array('i').fromaddress(b, 1)
            if a1[0] > a2[0]:
                res = -1
            res = 1
            return res
        a1 = ll_to_sort.byptr()
        a2 = _rawffi.Array('i')(1)
        a2[0] = len(ll_to_sort)
        a3 = _rawffi.Array('i')(1)
        a3[0] = struct.calcsize('i')
        cb = _rawffi.CallbackPtr(compare, ['P', 'P'], 'i')
        a4 = cb.byptr()
        qsort(a1, a2, a3, a4)
        res = [ll_to_sort[i] for i in range(len(ll_to_sort))]
        assert res == [1,2,3,4]
        a1.free()
        a2.free()
        a3.free()
        a4.free()
        ll_to_sort.free()
        del cb

    def test_another_callback(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        runcallback = lib.ptr('runcallback', ['P'], 'q')
        def callback():
            return 1<<42

        cb = _rawffi.CallbackPtr(callback, [], 'q')
        a1 = cb.byptr()
        res = runcallback(a1)
        assert res[0] == 1<<42
        res.free()
        a1.free()
        del cb

    def test_setattr_struct(self):
        import _rawffi
        X = _rawffi.Structure([('value1', 'i'), ('value2', 'i')])
        x = X(value1=1, value2=2)
        assert x.value1 == 1
        assert x.value2 == 2
        x.value1 = 3
        assert x.value1 == 3
        raises(AttributeError, "x.foo")
        raises(AttributeError, "x.foo = 1")
        x.free()

    def test_sizes_and_alignments(self):
        import _rawffi
        for k, (s, a) in self.sizes_and_alignments.iteritems():
            assert _rawffi.sizeof(k) == s
            assert _rawffi.alignment(k) == a

    def test_array_addressof(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        alloc = lib.ptr('allocate_array', [], 'P')
        A = _rawffi.Array('i')
        res = alloc()
        a = A.fromaddress(res[0], 1)
        res.free()
        assert a[0] == 3
        assert A.fromaddress(a.buffer, 1)[0] == 3

    def test_shape(self):
        import _rawffi
        A = _rawffi.Array('i')
        a = A(1)
        assert a.shape is A
        a.free()
        S = _rawffi.Structure([('v1', 'i')])
        s = S(v1=3)
        assert s.shape is S
        s.free()

    def test_negative_pointers(self):
        import _rawffi
        A = _rawffi.Array('P')
        a = A(1)
        a[0] = -1234
        a.free()
        
    def test_passing_raw_pointers(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        A = _rawffi.Array('i')
        get_array_elem = lib.ptr('get_array_elem', ['P', 'i'], 'i')
        a = A(1)
        a[0] = 3
        arg1 = _rawffi.Array('P')(1)
        arg1[0] = a.buffer
        arg2 = _rawffi.Array('i')(1)
        res = get_array_elem(arg1, arg2)
        assert res[0] == 3
        res.free()
        arg1.free()
        arg2.free()
        a.free()

    def test_repr(self):
        import _rawffi, struct
        s = struct.calcsize("i")
        assert (repr(_rawffi.Array('i')) ==
                "<_rawffi.Array 'i' (%d, %d)>" % (s, s))
        assert repr(_rawffi.Array((18, 2))) == "<_rawffi.Array '?' (18, 2)>"
        assert (repr(_rawffi.Structure([('x', 'i'), ('yz', 'i')])) ==
                "<_rawffi.Structure 'x' 'yz' (%d, %d)>" % (2*s, s))

        s = _rawffi.Structure([('x', 'i'), ('yz', 'i')])()
        assert repr(s) == "<_rawffi struct %x>" % (s.buffer,)
        s.free()
        a = _rawffi.Array('i')(5)
        assert repr(a) == "<_rawffi array %x of length %d>" % (a.buffer,
                                                               len(a))
        a.free()

    def test_wide_char(self):
        import _rawffi
        A = _rawffi.Array('u')
        a = A(3)
        a[0] = u'x'
        a[1] = u'y'
        a[2] = u'z'
        assert a[0] == u'x'
        b = _rawffi.Array('c').fromaddress(a.buffer, 38)
        assert b[0] == 'x'
        assert b[1] == '\x00'
        assert b[2] == '\x00'
        assert b[3] == '\x00'
        assert b[4] == 'y'
        a.free()

    def test_truncate(self):
        import _rawffi, struct
        a = _rawffi.Array('b')(1)
        a[0] = -5
        assert a[0] == -5
        a[0] = 123L
        assert a[0] == 123
        a[0] = 0x97817182ab128111111111111171817d042
        assert a[0] == 0x42
        a[0] = 255
        assert a[0] == -1
        a[0] = -2
        assert a[0] == -2
        a[0] = -255
        assert a[0] == 1
        a.free()

        a = _rawffi.Array('B')(1)
        a[0] = 123L
        assert a[0] == 123
        a[0] = 0x18329b1718b97d89b7198db817d042
        assert a[0] == 0x42
        a[0] = 255
        assert a[0] == 255
        a[0] = -2
        assert a[0] == 254
        a[0] = -255
        assert a[0] == 1
        a.free()

        a = _rawffi.Array('h')(1)
        a[0] = 123L
        assert a[0] == 123
        a[0] = 0x9112cbc91bd91db19aaaaaaaaaaaaaa8170d42
        assert a[0] == 0x0d42
        a[0] = 65535
        assert a[0] == -1
        a[0] = -2
        assert a[0] == -2
        a[0] = -65535
        assert a[0] == 1
        a.free()

        a = _rawffi.Array('H')(1)
        a[0] = 123L
        assert a[0] == 123
        a[0] = 0xeeeeeeeeeeeeeeeeeeeeeeeeeeeee817d042
        assert a[0] == 0xd042
        a[0] = -2
        assert a[0] == 65534
        a.free()

        maxptr = (256 ** struct.calcsize("P")) - 1
        a = _rawffi.Array('P')(1)
        a[0] = 123L
        assert a[0] == 123
        a[0] = 0xeeeeeeeeeeeeeeeeeeeeeeeeeeeee817d042
        assert a[0] == 0xeeeeeeeeeeeeeeeeeeeeeeeeeeeee817d042 & maxptr
        a[0] = -2
        assert a[0] == maxptr - 1
        a.free()

    def test_getprimitive(self):
        import _rawffi
        lib = _rawffi.CDLL(self.lib_name)
        a = lib.getprimitive("l", "static_int")
        assert a[0] == 42
        a = lib.getprimitive("d", "static_double")
        assert a[0] == 42.42
        raises(ValueError, lib.getprimitive, 'z', 'ddddddd')
        raises(ValueError, lib.getprimitive, 'zzz', 'static_int')

