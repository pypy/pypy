import py
import sys

class TestSimpleTypes:

    def setup_class(cls):
        import ctypes
        try:
            from _ctypes import set_conversion_mode
        except ImportError:
            pass
        else:
            cls.prev_conv_mode = set_conversion_mode("ascii", "strict")

    def teardown_class(cls):
        try:
            from _ctypes import set_conversion_mode
        except ImportError:
            pass
        else:
            set_conversion_mode(*cls.prev_conv_mode)


    def test_subclasses(self):
        py.test.skip("subclassing semantics not implemented")
        from ctypes import c_void_p, c_char_p
        # ctypes 0.9.5 and before did overwrite from_param in SimpleType_new
        class CVOIDP(c_void_p):
            def from_param(cls, value):
                return value * 2
            from_param = classmethod(from_param)

        class CCHARP(c_char_p):
            def from_param(cls, value):
                return value * 4
            from_param = classmethod(from_param)

        assert CVOIDP.from_param("abc") == "abcabc"
        assert CCHARP.from_param("abc") == "abcabcabcabc"

        try:
            from ctypes import c_wchar_p
        except ImportError:
            return

        class CWCHARP(c_wchar_p):
            def from_param(cls, value):
                return value * 3
            from_param = classmethod(from_param)

        assert CWCHARP.from_param("abc") == "abcabcabc"

    # XXX Replace by c_char_p tests
    def test_cstrings(self):
        py.test.skip("testing implementation internals")
        from ctypes import c_char_p, byref

        # c_char_p.from_param on a Python String packs the string
        # into a cparam object
        s = "123"
        assert c_char_p.from_param(s)._obj is s

        # new in 0.9.1: convert (encode) unicode to ascii
        assert c_char_p.from_param(u"123")._obj == "123"
        raises(UnicodeEncodeError, c_char_p.from_param, u"123\377")

        raises(TypeError, c_char_p.from_param, 42)

        # calling c_char_p.from_param with a c_char_p instance
        # returns the argument itself:
        a = c_char_p("123")
        assert c_char_p.from_param(a) is a

    def test_cw_strings(self):
        from ctypes import byref
        try:
            from ctypes import c_wchar_p
        except ImportError:
##            print "(No c_wchar_p)"
            return
        s = u"123"
        if sys.platform == "win32":
            assert c_wchar_p.from_param(s)._obj is s
            raises(TypeError, c_wchar_p.from_param, 42)

            # new in 0.9.1: convert (decode) ascii to unicode
            assert c_wchar_p.from_param("123")._obj == u"123"
        raises(UnicodeDecodeError, c_wchar_p.from_param, "123\377")

        pa = c_wchar_p.from_param(c_wchar_p(u"123"))
        assert type(pa) == c_wchar_p

    def test_int_pointers(self):
        from ctypes import c_short, c_uint, c_int, c_long, POINTER, pointer
        LPINT = POINTER(c_int)

##        p = pointer(c_int(42))
##        x = LPINT.from_param(p)
        x = LPINT.from_param(pointer(c_int(42)))
        assert x.contents.value == 42
        assert LPINT(c_int(42)).contents.value == 42

        assert not LPINT.from_param(None)

        if c_int != c_long:
            raises(TypeError, LPINT.from_param, pointer(c_long(42)))
        raises(TypeError, LPINT.from_param, pointer(c_uint(42)))
        raises(TypeError, LPINT.from_param, pointer(c_short(42)))

    def test_byref_pointer(self):
        # The from_param class method of POINTER(typ) classes accepts what is
        # returned by byref(obj), it type(obj) == typ
        from ctypes import c_short, c_uint, c_int, c_long, pointer, POINTER, byref
        LPINT = POINTER(c_int)

        LPINT.from_param(byref(c_int(42)))

        raises(TypeError, LPINT.from_param, byref(c_short(22)))
        if c_int != c_long:
            raises(TypeError, LPINT.from_param, byref(c_long(22)))
        raises(TypeError, LPINT.from_param, byref(c_uint(22)))

    def test_byref_pointerpointer(self):
        # See above
        from ctypes import c_short, c_uint, c_int, c_long, pointer, POINTER, byref

        LPLPINT = POINTER(POINTER(c_int))
        LPLPINT.from_param(byref(pointer(c_int(42))))

        raises(TypeError, LPLPINT.from_param, byref(pointer(c_short(22))))
        if c_int != c_long:
            raises(TypeError, LPLPINT.from_param, byref(pointer(c_long(22))))
        raises(TypeError, LPLPINT.from_param, byref(pointer(c_uint(22))))

    def test_array_pointers(self):
        from ctypes import c_short, c_uint, c_int, c_long, POINTER
        INTARRAY = c_int * 3
        ia = INTARRAY()
        assert len(ia) == 3
        assert [ia[i] for i in range(3)] == [0, 0, 0]

        # Pointers are only compatible with arrays containing items of
        # the same type!
        LPINT = POINTER(c_int)
        LPINT.from_param((c_int*3)())
        raises(TypeError, LPINT.from_param, c_short*3)
        raises(TypeError, LPINT.from_param, c_long*3)
        raises(TypeError, LPINT.from_param, c_uint*3)

##    def test_performance(self):
##        check_perf()

    def test_noctypes_argtype(self):
        py.test.skip("we implement details differently")
        from ctypes import CDLL, c_void_p, ArgumentError
        import conftest
        dll = CDLL(str(conftest.sofile))

        func = dll._testfunc_p_p
        func.restype = c_void_p
        # TypeError: has no from_param method
        raises(TypeError, setattr, func, "argtypes", (object,))

        class Adapter(object):
            def from_param(cls, obj):
                return None

        func.argtypes = (Adapter(),)
        assert func(None) == None
        assert func(object()) == None

        class Adapter(object):
            def from_param(cls, obj):
                return obj

        func.argtypes = (Adapter(),)
        # don't know how to convert parameter 1
        raises(ArgumentError, func, object())
        assert func(c_void_p(42)) == 42

        class Adapter(object):
            def from_param(cls, obj):
                raise ValueError(obj)

        func.argtypes = (Adapter(),)
        # ArgumentError: argument 1: ValueError: 99
        raises(ArgumentError, func, 99)
