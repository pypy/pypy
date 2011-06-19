"""
Here is probably the place to write the docs, since the test-cases
show how the type behave.

Later...
"""

from ctypes import *
import sys
import py
from support import BaseCTypesTestChecker

try:
    WINFUNCTYPE
except NameError:
    # fake to enable this test on Linux
    WINFUNCTYPE = CFUNCTYPE


def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.dll = CDLL(_ctypes_test)
    if sys.platform == "win32":
        mod.windll = WinDLL(_ctypes_test)

class POINT(Structure):
    _fields_ = [("x", c_int), ("y", c_int)]
class RECT(Structure):
    _fields_ = [("left", c_int), ("top", c_int),
                ("right", c_int), ("bottom", c_int)]

class TestFunctions(BaseCTypesTestChecker):

    def test_mro(self):
        # in Python 2.3, this raises TypeError: MRO conflict among bases classes,
        # in Python 2.2 it works.
        #
        # But in early versions of _ctypes.c, the result of tp_new
        # wasn't checked, and it even crashed Python.
        # Found by Greg Chapman.

        try:
            class X(object, Array):
                _length_ = 5
                _type_ = "i"
        except TypeError:
            pass


        from _ctypes import _Pointer
        try:
            class X(object, _Pointer):
                pass
        except TypeError:
            pass

        from _ctypes import _SimpleCData
        try:
            class X(object, _SimpleCData):
                _type_ = "i"
        except TypeError:
            pass

        try:
            class X(object, Structure):
                _fields_ = []
        except TypeError:
            pass


    def test_wchar_parm(self):
        try:
            c_wchar
        except NameError:
            return
        f = dll._testfunc_i_bhilfd
        f.argtypes = [c_byte, c_wchar, c_int, c_long, c_float, c_double]
        result = f(1, u"x", 3, 4, 5.0, 6.0)
        assert result == 139
        assert type(result) == int

    def test_wchar_result(self):
        try:
            c_wchar
        except NameError:
            return
        f = dll._testfunc_i_bhilfd
        f.argtypes = [c_byte, c_short, c_int, c_long, c_float, c_double]
        f.restype = c_wchar
        result = f(0, 0, 0, 0, 0, 0)
        assert result == u'\x00'

    def test_char_result(self):
        f = dll._testfunc_i_bhilfd
        f.argtypes = [c_byte, c_short, c_int, c_long, c_float, c_double]
        f.restype = c_char
        result = f(0, 0, 0, 0, 0, 0)
        assert result == '\x00'

    def test_voidresult(self):
        f = dll._testfunc_v
        f.restype = None
        f.argtypes = [c_int, c_int, POINTER(c_int)]
        result = c_int()
        assert None == f(1, 2, byref(result))
        assert result.value == 3

    def test_intresult(self):
        f = dll._testfunc_i_bhilfd
        f.argtypes = [c_byte, c_short, c_int, c_long, c_float, c_double]
        f.restype = c_int
        result = f(1, 2, 3, 4, 5.0, 6.0)
        assert result == 21
        assert type(result) == int

        result = f(-1, -2, -3, -4, -5.0, -6.0)
        assert result == -21
        assert type(result) == int

        # If we declare the function to return a short,
        # is the high part split off?
        f.restype = c_short
        result = f(1, 2, 3, 4, 5.0, 6.0)
        assert result == 21
        assert type(result) == int

        result = f(1, 2, 3, 0x10004, 5.0, 6.0)
        assert result == 21
        assert type(result) == int

        # You cannot assing character format codes as restype any longer
        raises(TypeError, setattr, f, "restype", "i")

    def test_floatresult(self):
        f = dll._testfunc_f_bhilfd
        f.argtypes = [c_byte, c_short, c_int, c_long, c_float, c_double]
        f.restype = c_float
        result = f(1, 2, 3, 4, 5.0, 6.0)
        assert result == 21
        assert type(result) == float

        result = f(-1, -2, -3, -4, -5.0, -6.0)
        assert result == -21
        assert type(result) == float

    def test_doubleresult(self):
        f = dll._testfunc_d_bhilfd
        f.argtypes = [c_byte, c_short, c_int, c_long, c_float, c_double]
        f.restype = c_double
        result = f(1, 2, 3, 4, 5.0, 6.0)
        assert result == 21
        assert type(result) == float

        result = f(-1, -2, -3, -4, -5.0, -6.0)
        assert result == -21
        assert type(result) == float

    def test_longlongresult(self):
        try:
            c_longlong
        except NameError:
            return
        f = dll._testfunc_q_bhilfd
        f.restype = c_longlong
        f.argtypes = [c_byte, c_short, c_int, c_long, c_float, c_double]
        result = f(1, 2, 3, 4, 5.0, 6.0)
        assert result == 21

        f = dll._testfunc_q_bhilfdq
        f.restype = c_longlong
        f.argtypes = [c_byte, c_short, c_int, c_long, c_float, c_double, c_longlong]
        result = f(1, 2, 3, 4, 5.0, 6.0, 21)
        assert result == 42

    def test_stringresult(self):
        f = dll._testfunc_p_p
        f.argtypes = None
        f.restype = c_char_p
        result = f("123")
        assert result == "123"

        result = f(None)
        assert result == None

    def test_pointers(self):
        f = dll._testfunc_p_p
        f.restype = POINTER(c_int)
        f.argtypes = [POINTER(c_int)]

        # This only works if the value c_int(42) passed to the
        # function is still alive while the pointer (the result) is
        # used.

        v = c_int(42)

        assert pointer(v).contents.value == 42
        result = f(pointer(v))
        assert type(result) == POINTER(c_int)
        assert result.contents.value == 42

        # This on works...
        result = f(pointer(v))
        assert result.contents.value == v.value

        p = pointer(c_int(99))
        result = f(p)
        assert result.contents.value == 99

        arg = byref(v)
        result = f(arg)
        assert not result.contents == v.value

        raises(ArgumentError, f, byref(c_short(22)))

        # It is dangerous, however, because you don't control the lifetime
        # of the pointer:
        result = f(byref(c_int(99)))
        assert not result.contents == 99

    def test_convert_pointers(self):
        f = dll.deref_LP_c_char_p
        f.restype = c_char
        f.argtypes = [POINTER(c_char_p)]
        #
        s = c_char_p('hello world')
        ps = pointer(s)
        assert f(ps) == 'h'
        assert f(s) == 'h'  # automatic conversion from char** to char*

    def test_errors_1(self):
        f = dll._testfunc_p_p
        f.argtypes = [POINTER(c_int)]
        f.restype = c_int

        class X(Structure):
            _fields_ = [("y", c_int)]

        raises(ArgumentError, f, X()) #cannot convert parameter

    ################################################################
    def test_shorts(self):
        f = dll._testfunc_callback_i_if

        args = []
        expected = [262144, 131072, 65536, 32768, 16384, 8192, 4096, 2048,
                    1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]

        def callback(v):
            args.append(v)
            return v

        CallBack = CFUNCTYPE(c_int, c_int)

        cb = CallBack(callback)
        f(2**18, cb)
        assert args == expected

    ################################################################


    def test_callbacks(self):
        f = dll._testfunc_callback_i_if
        f.restype = c_int

        MyCallback = CFUNCTYPE(c_int, c_int)

        def callback(value):
            #print "called back with", value
            return value

        cb = MyCallback(callback)
        result = f(-10, cb)
        assert result == -18

        # test with prototype
        f.argtypes = [c_int, MyCallback]
        cb = MyCallback(callback)
        result = f(-10, cb)
        assert result == -18

        AnotherCallback = WINFUNCTYPE(c_int, c_int, c_int, c_int, c_int)

        # check that the prototype works: we call f with wrong
        # argument types
        cb = AnotherCallback(callback)
        raises(ArgumentError, f, -10, cb)


    def test_callbacks_2(self):
        # Can also use simple datatypes as argument type specifiers
        # for the callback function.
        # In this case the call receives an instance of that type
        f = dll._testfunc_callback_i_if
        f.restype = c_int

        MyCallback = CFUNCTYPE(c_int, c_int)

        f.argtypes = [c_int, MyCallback]

        def callback(value):
            #print "called back with", value
            assert type(value) == int
            return value

        cb = MyCallback(callback)
        result = f(-10, cb)
        assert result == -18

    def test_longlong_callbacks(self):

        f = dll._testfunc_callback_q_qf
        f.restype = c_longlong

        MyCallback = CFUNCTYPE(c_longlong, c_longlong)

        f.argtypes = [c_longlong, MyCallback]

        def callback(value):
            assert isinstance(value, (int, long))
            return value & 0x7FFFFFFF

        cb = MyCallback(callback)

        assert 13577625587 == f(1000000000000, cb)

    def test_errors_2(self):
        raises(AttributeError, getattr, dll, "_xxx_yyy")
        raises(ValueError, c_int.in_dll, dll, "_xxx_yyy")

    def test_byval(self):
        # without prototype
        ptin = POINT(1, 2)
        ptout = POINT()
        # EXPORT int _testfunc_byval(point in, point *pout)
        result = dll._testfunc_byval(ptin, byref(ptout))
        got = result, ptout.x, ptout.y
        expected = 3, 1, 2
        assert got == expected

        # with prototype
        ptin = POINT(101, 102)
        ptout = POINT()
        dll._testfunc_byval.argtypes = (POINT, POINTER(POINT))
        dll._testfunc_byval.restype = c_int
        result = dll._testfunc_byval(ptin, byref(ptout))
        got = result, ptout.x, ptout.y
        expected = 203, 101, 102
        assert got == expected

    def test_struct_return_2H(self):
        class S2H(Structure):
            _fields_ = [("x", c_short),
                        ("y", c_short)]
        dll.ret_2h_func.restype = S2H
        dll.ret_2h_func.argtypes = [S2H]
        inp = S2H(99, 88)
        s2h = dll.ret_2h_func(inp)
        assert (s2h.x, s2h.y) == (99*2, 88*3)

    if sys.platform == "win32":
        def test_struct_return_2H_stdcall(self):
            class S2H(Structure):
                _fields_ = [("x", c_short),
                            ("y", c_short)]

            windll.s_ret_2h_func.restype = S2H
            windll.s_ret_2h_func.argtypes = [S2H]
            s2h = windll.s_ret_2h_func(S2H(99, 88))
            assert (s2h.x, s2h.y) == (99*2, 88*3)

    def test_struct_return_8H(self):
        class S8I(Structure):
            _fields_ = [("a", c_int),
                        ("b", c_int),
                        ("c", c_int),
                        ("d", c_int),
                        ("e", c_int),
                        ("f", c_int),
                        ("g", c_int),
                        ("h", c_int)]
        dll.ret_8i_func.restype = S8I
        dll.ret_8i_func.argtypes = [S8I]
        inp = S8I(9, 8, 7, 6, 5, 4, 3, 2)
        s8i = dll.ret_8i_func(inp)
        assert (s8i.a, s8i.b, s8i.c, s8i.d, s8i.e, s8i.f, s8i.g, s8i.h) == (
                             (9*2, 8*3, 7*4, 6*5, 5*6, 4*7, 3*8, 2*9))

    if sys.platform == "win32":
        def test_struct_return_8H_stdcall(self):
            class S8I(Structure):
                _fields_ = [("a", c_int),
                            ("b", c_int),
                            ("c", c_int),
                            ("d", c_int),
                            ("e", c_int),
                            ("f", c_int),
                            ("g", c_int),
                            ("h", c_int)]
            windll.s_ret_8i_func.restype = S8I
            windll.s_ret_8i_func.argtypes = [S8I]
            inp = S8I(9, 8, 7, 6, 5, 4, 3, 2)
            s8i = windll.s_ret_8i_func(inp)
            assert (s8i.a, s8i.b, s8i.c, s8i.d, s8i.e, s8i.f, s8i.g, s8i.h) == (
                                 (9*2, 8*3, 7*4, 6*5, 5*6, 4*7, 3*8, 2*9))

    def test_call_some_args(self):
        f = dll.my_strchr
        f.argtypes = [c_char_p]
        f.restype = c_char_p
        result = f("abcd", ord("b"))
        assert result == "bcd"

    def test_caching_bug_1(self):
        # the same test as test_call_some_args, with two extra lines
        # in the middle that trigger caching in f._ptr, which then
        # makes the last two lines fail
        f = dll.my_strchr
        f.argtypes = [c_char_p, c_int]
        f.restype = c_char_p
        result = f("abcd", ord("b"))
        assert result == "bcd"
        result = f("abcd", ord("b"), 42)
        assert result == "bcd"

    def test_sf1651235(self):
        py.test.skip("we are less strict in checking callback parameters")
        # see http://www.python.org/sf/1651235

        proto = CFUNCTYPE(c_int, RECT, POINT)
        def callback(*args):
            return 0

        callback = proto(callback)
        raises(ArgumentError, lambda: callback((1, 2, 3, 4), POINT()))

    def test_union_as_passed_value(self):
        class UN(Union):
            _fields_ = [("x", c_short),
                        ("y", c_long)]
        dll.ret_un_func.restype = UN
        dll.ret_un_func.argtypes = [UN]
        A = UN * 2
        a = A()
        a[1].x = 33
        u = dll.ret_un_func(a[1])
        assert u.y == 33*10000

    def test_cache_funcptr(self):
        tf_b = dll.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_byte,)
        assert tf_b(-126) == -42
        ptr = tf_b._ptr
        assert ptr is not None
        assert tf_b(-126) == -42
        assert tf_b._ptr is ptr

    def test_warnings(self):
        import warnings
        warnings.simplefilter("always")
        with warnings.catch_warnings(record=True) as w:
            dll.get_an_integer()
            assert len(w) == 2
            assert issubclass(w[0].category, RuntimeWarning)
            assert issubclass(w[1].category, RuntimeWarning)
            assert "C function without declared arguments called" in str(w[0].message)
            assert "C function without declared return type called" in str(w[1].message)

    def test_errcheck(self):
        py.test.skip('fixme')
        def errcheck(result, func, args):
            assert result == -42
            assert type(result) is int
            arg, = args
            assert arg == -126
            assert type(arg) is int
            return result
        #
        tf_b = dll.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_byte,)
        tf_b.errcheck = errcheck
        assert tf_b(-126) == -42
        del tf_b.errcheck
        with warnings.catch_warnings(record=True) as w:
            dll.get_an_integer.argtypes = []
            dll.get_an_integer()
            assert len(w) == 1
            assert issubclass(w[0].category, RuntimeWarning)
            assert "C function without declared return type called" in str(w[0].message)
            
        with warnings.catch_warnings(record=True) as w:
            dll.get_an_integer.restype = None
            dll.get_an_integer()
            assert len(w) == 0
            
        warnings.resetwarnings()
