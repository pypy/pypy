from ctypes import *
import py
from support import BaseCTypesTestChecker

class TestCallbacks(BaseCTypesTestChecker):
    functype = CFUNCTYPE

##    def tearDown(self):
##        import gc
##        gc.collect()

    def callback(self, *args):
        self.got_args = args
        return args[-1]

    def check_type(self, typ, arg):
        unwrapped_types = {
            c_float: (float,),
            c_double: (float,),
            c_char: (str,),
            c_char_p: (str,),
            c_uint: (int, long),
            c_ulong: (int, long),
            }
        
        PROTO = self.functype.im_func(typ, typ)
        cfunc = PROTO(self.callback)
        result = cfunc(arg)
        if typ == c_float:
            assert abs(result - arg) < 0.000001
        else:
            assert self.got_args == (arg,)
            assert result == arg

        result2 = cfunc(typ(arg))
        assert type(result2) in unwrapped_types.get(typ, (int, long))

        PROTO = self.functype.im_func(typ, c_byte, typ)
        result = PROTO(self.callback)(-3, arg)
        if typ == c_float:
            assert abs(result - arg) < 0.000001
        else:
            assert self.got_args == (-3, arg)
            assert result == arg

    ################

    def test_byte(self):
        self.check_type(c_byte, 42)
        self.check_type(c_byte, -42)

    def test_ubyte(self):
        self.check_type(c_ubyte, 42)

    def test_short(self):
        self.check_type(c_short, 42)
        self.check_type(c_short, -42)

    def test_ushort(self):
        self.check_type(c_ushort, 42)

    def test_int(self):
        self.check_type(c_int, 42)
        self.check_type(c_int, -42)

    def test_uint(self):
        self.check_type(c_uint, 42)

    def test_long(self):
        self.check_type(c_long, 42)
        self.check_type(c_long, -42)

    def test_ulong(self):
        self.check_type(c_ulong, 42)

    def test_longlong(self):
        self.check_type(c_longlong, 42)
        self.check_type(c_longlong, -42)

    def test_ulonglong(self):
        self.check_type(c_ulonglong, 42)

    def test_float(self):
        # only almost equal: double -> float -> double
        import math
        self.check_type(c_float, math.e)
        self.check_type(c_float, -math.e)

    def test_double(self):
        self.check_type(c_double, 3.14)
        self.check_type(c_double, -3.14)

    def test_char(self):
        self.check_type(c_char, "x")
        self.check_type(c_char, "a")

    # disabled: would now (correctly) raise a RuntimeWarning about
    # a memory leak.  A callback function cannot return a non-integral
    # C type without causing a memory leak.
##    def test_char_p(self):
##        self.check_type(c_char_p, "abc")
##        self.check_type(c_char_p, "def")

    def test_unsupported_restype_1(self):
        py.test.skip("we are less strict about callback return type sanity")
        # Only "fundamental" result types are supported for callback
        # functions, the type must have a non-NULL stgdict->setfunc.
        # POINTER(c_double), for example, is not supported.

        prototype = self.functype.im_func(POINTER(c_double))
        # The type is checked when the prototype is called
        raises(TypeError, prototype, lambda: None)

try:
    WINFUNCTYPE
except NameError:
    pass
else:
    class TestStdcallCallbacks(TestCallbacks):
        functype = WINFUNCTYPE

################################################################

class TestSampleCallbacks(BaseCTypesTestChecker):

    def test_integrate(self):
        # Derived from some then non-working code, posted by David Foster
        import conftest
        _ctypes_test = str(conftest.sofile)
        dll = CDLL(_ctypes_test)

        # The function prototype called by 'integrate': double func(double);
        CALLBACK = CFUNCTYPE(c_double, c_double)

        # The integrate function itself, exposed from the _ctypes_test dll
        integrate = dll.integrate
        integrate.argtypes = (c_double, c_double, CALLBACK, c_long)
        integrate.restype = c_double

        def func(x):
            return x**2

        result = integrate(0.0, 1.0, CALLBACK(func), 10)
        diff = abs(result - 1./3.)

        assert diff < 0.01, "%s not less than 0.01" % diff

################################################################

class TestMoreCallbacks(BaseCTypesTestChecker):

    def test_callback_with_struct_argument(self):
        py.test.skip("callbacks with struct arguments not implemented yet")
        class RECT(Structure):
            _fields_ = [("left", c_int), ("top", c_int),
                        ("right", c_int), ("bottom", c_int)]

        proto = CFUNCTYPE(c_int, RECT)
        def callback(point):
            return point.left+point.top+point.right+point.bottom

        cbp = proto(callback)

        rect = RECT(1000,100,10,1)

        res = cbp(rect)

        assert res == 1111

    def test_callback_unsupported_return_struct(self):
        class RECT(Structure):
            _fields_ = [("left", c_int), ("top", c_int),
                        ("right", c_int), ("bottom", c_int)]
        
        proto = CFUNCTYPE(RECT, c_int)
        raises(TypeError, proto, lambda r: 0)


    def test_qsort(self):
        import conftest
        _ctypes_test = str(conftest.sofile)
        dll = CDLL(_ctypes_test)

        PI = POINTER(c_int)
        A = c_int*5
        a = A()
        for i in range(5):
            a[i] = 5-i

        assert a[0] == 5 # sanity
        
        def comp(a, b):
            a = a.contents.value
            b = b.contents.value
            return cmp(a,b)
        qs = dll.my_qsort
        qs.restype = None
        CMP = CFUNCTYPE(c_int, PI, PI)
        qs.argtypes = (PI, c_size_t, c_size_t, CMP)

        qs(cast(a, PI), 5, sizeof(c_int), CMP(comp))

        res = list(a)

        assert res == [1,2,3,4,5]

    def test_pyobject_as_opaque(self):
        import conftest
        _ctypes_test = str(conftest.sofile)
        dll = CDLL(_ctypes_test)

        def callback(arg):
            return arg()

        CTP = CFUNCTYPE(c_int, py_object)
        cfunc = dll._testfunc_callback_opaque
        cfunc.argtypes = [CTP, py_object]
        cfunc.restype = c_int
        res = cfunc(CTP(callback), lambda : 3)
        assert res == 3

    def test_callback_void(self, capsys):
        import conftest
        _ctypes_test = str(conftest.sofile)
        dll = CDLL(_ctypes_test)

        def callback():
            pass

        CTP = CFUNCTYPE(None)
        cfunc = dll._testfunc_callback_void
        cfunc.argtypes = [CTP]
        cfunc.restype = int
        cfunc(CTP(callback))
        out, err = capsys.readouterr()
        assert (out, err) == ("", "")


    def test_callback_pyobject(self):
        def callback(obj):
            return obj

        FUNC = CFUNCTYPE(py_object, py_object)
        cfunc = FUNC(callback)
        param = c_int(42)
        assert cfunc(param) is param

    def test_raise_argumenterror(self):
        py.test.skip('FIXME')
        def callback(x):
            pass
        FUNC = CFUNCTYPE(None, c_void_p)
        cfunc = FUNC(callback)
        param = c_uint(42)
        py.test.raises(ArgumentError, "cfunc(param)")
