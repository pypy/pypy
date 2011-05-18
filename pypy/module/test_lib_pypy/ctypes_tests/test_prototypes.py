import py
from ctypes import *
from support import BaseCTypesTestChecker

# IMPORTANT INFO:
#
# Consider this call:
#    func.restype = c_char_p
#    func(c_char_p("123"))
# It returns
#    "123"
#
# WHY IS THIS SO?
#
# argument tuple (c_char_p("123"), ) is destroyed after the function
# func is called, but NOT before the result is actually built.
#
# If the arglist would be destroyed BEFORE the result has been built,
# the c_char_p("123") object would already have a zero refcount,
# and the pointer passed to (and returned by) the function would
# probably point to deallocated space.
#
# In this case, there would have to be an additional reference to the argument...

def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.testdll = CDLL(_ctypes_test)

class TestFuncPrototypes(BaseCTypesTestChecker):

    def test_restype_setattr(self):
        func = testdll._testfunc_p_p
        raises(TypeError, setattr, func, 'restype', 20)

    def test_argtypes_setattr(self):
        func = testdll._testfunc_p_p
        raises(TypeError, setattr, func, 'argtypes', 20)
        raises(TypeError, setattr, func, 'argtypes', [20])

        func = CFUNCTYPE(c_long, c_void_p, c_long)(lambda: None)
        assert func.argtypes == (c_void_p, c_long)

    def test_paramflags_setattr(self):
        func = CFUNCTYPE(c_long, c_void_p, c_long)(lambda: None)
        raises(TypeError, setattr, func, 'paramflags', 'spam')
        raises(ValueError, setattr, func, 'paramflags', (1, 2, 3, 4))
        raises(TypeError, setattr, func, 'paramflags', ((1,), ('a',)))
        func.paramflags = (1,), (1|4,)

    def test_kwargs(self):
        proto = CFUNCTYPE(c_char_p, c_char_p, c_int)
        paramflags = (1, 'text', "tavino"), (1, 'letter', ord('v'))
        func = proto(('my_strchr', testdll), paramflags)
        assert func.argtypes == (c_char_p, c_int)
        assert func.restype == c_char_p

        result = func("abcd", ord('b'))
        assert result == "bcd"

        result = func()
        assert result == "vino"

        result = func("grapevine")
        assert result == "vine"

        result = func(text="grapevine")
        assert result == "vine"

        result = func(letter=ord('i'))
        assert result == "ino"

        result = func(letter=ord('p'), text="impossible")
        assert result == "possible"

        result = func(text="impossible", letter=ord('p'))
        assert result == "possible"

# Return machine address `a` as a (possibly long) non-negative integer.
# Starting with Python 2.5, id(anything) is always non-negative, and
# the ctypes addressof() inherits that via PyLong_FromVoidPtr().
def positive_address(a):
    if a >= 0:
        return a
    # View the bits in `a` as unsigned instead.
    import struct
    num_bits = struct.calcsize("P") * 8 # num bits in native machine address
    a += 1L << num_bits
    assert a >= 0
    return a

def c_wbuffer(init):
    n = len(init) + 1
    return (c_wchar * n)(*init)

class TestCharPointers(BaseCTypesTestChecker):

    def test_int_pointer_arg(self):
        func = testdll._testfunc_p_p
        func.restype = c_long
        assert 0 == func(0)

        ci = c_int(0)

        func.argtypes = POINTER(c_int),
        assert positive_address(addressof(ci)) == (
                             positive_address(func(byref(ci))))

        func.argtypes = c_char_p,
        raises(ArgumentError, func, byref(ci))

        func.argtypes = POINTER(c_short),
        raises(ArgumentError, func, byref(ci))

        func.argtypes = POINTER(c_double),
        raises(ArgumentError, func, byref(ci))

    def test_POINTER_c_char_arg(self):
        func = testdll._testfunc_p_p
        func.restype = c_char_p
        func.argtypes = POINTER(c_char),

        assert None == func(None)
        assert "123" == func("123")
        assert None == func(c_char_p(None))
        assert "123" == func(c_char_p("123"))

        assert "123" == func(c_buffer("123"))
        ca = c_char("a")
        assert "a" == func(pointer(ca))[0]
        assert "a" == func(byref(ca))[0]

    def test_c_char_p_arg(self):
        func = testdll._testfunc_p_p
        func.restype = c_char_p
        func.argtypes = c_char_p,

        assert None == func(None)
        assert "123" == func("123")
        assert None == func(c_char_p(None))
        assert "123" == func(c_char_p("123"))

        assert "123" == func(c_buffer("123"))
        ca = c_char("a")
        assert "a" == func(pointer(ca))[0]
        assert "a" == func(byref(ca))[0]

    def test_c_void_p_arg(self):
        func = testdll._testfunc_p_p
        func.restype = c_char_p
        func.argtypes = c_void_p,

        assert None == func(None)
        assert "123" == func("123")
        assert "123" == func(c_char_p("123"))
        assert None == func(c_char_p(None))

        assert "123" == func(c_buffer("123"))
        ca = c_char("a")
        assert "a" == func(pointer(ca))[0]
        assert "a" == func(byref(ca))[0]

        func(byref(c_int()))
        func(pointer(c_int()))
        func((c_int * 3)())

        try:
            func.restype = c_wchar_p
        except NameError:
            pass
        else:
            assert None == func(c_wchar_p(None))
            assert u"123" == func(c_wchar_p(u"123"))

    def test_instance(self):
        func = testdll._testfunc_p_p
        func.restype = c_void_p

        class X:
            _as_parameter_ = None

        func.argtypes = c_void_p,
        assert None == func(X())

        func.argtypes = None
        assert None == func(X())

try:
    c_wchar
except NameError:
    pass
else:
    class TestWCharPointers(BaseCTypesTestChecker):

        def setup_class(cls):
            func = testdll._testfunc_p_p
            func.restype = c_int
            func.argtypes = None
            cls.func = func
            BaseCTypesTestChecker.setup_class.im_func(cls)


        def test_POINTER_c_wchar_arg(self):
            func = self.func
            func.restype = c_wchar_p
            func.argtypes = POINTER(c_wchar),

            assert None == func(None)
            assert u"123" == func(u"123")
            assert None == func(c_wchar_p(None))
            assert u"123" == func(c_wchar_p(u"123"))

            assert u"123" == func(c_wbuffer(u"123"))
            ca = c_wchar("a")
            assert u"a" == func(pointer(ca))[0]
            assert u"a" == func(byref(ca))[0]

        def test_c_wchar_p_arg(self):
            func = self.func
            func.restype = c_wchar_p
            func.argtypes = c_wchar_p,

            c_wchar_p.from_param(u"123")

            assert None == func(None)
            assert "123" == func(u"123")
            assert None == func(c_wchar_p(None))
            assert "123" == func(c_wchar_p("123"))

            # XXX Currently, these raise TypeErrors, although they shouldn't:
            assert "123" == func(c_wbuffer("123"))
            ca = c_wchar("a")
            assert "a" == func(pointer(ca))[0]
            assert "a" == func(byref(ca))[0]

class TestArray(BaseCTypesTestChecker):
    def test(self):
        func = testdll._testfunc_ai8
        func.restype = POINTER(c_int)
        func.argtypes = c_int * 8,

        func((c_int * 8)(1, 2, 3, 4, 5, 6, 7, 8))

        # This did crash before:

        def func(): pass
        CFUNCTYPE(None, c_int * 3)(func)

################################################################

if __name__ == '__main__':
    unittest.main()
