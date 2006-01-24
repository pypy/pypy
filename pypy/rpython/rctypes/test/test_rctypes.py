import py.test
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile
from pypy.translator.tool.cbuild import compile_c_module
import sys
    

def setup_module(mod):
    try:
        import ctypes
    except ImportError:
        py.test.skip("this test needs ctypes installed")
    else:
        from pypy.rpython.rctypes.interface import cdll, c_char_p, c_int, c_char, POINTER, Structure, byref
        if sys.platform == 'win32':
            mylib = cdll.LoadLibrary('msvcrt.dll')
        elif sys.platform == 'linux2':
            mylib = cdll.LoadLibrary('libc.so.6')
        else:
            py.test.skip("don't know how to load the c lib for %s" % 
                    sys.platform)

        atoi = mylib.atoi
        atoi.restype = c_int
        atoi.argtypes = [c_char_p]
        atoi.argtypes = [POINTER(c_char)]
        def o_atoi(a):
           return atoi(a)
        mod.o_atoi = o_atoi
        mod.cdll = cdll
        class tagpoint(Structure):
            _fields_ = [("x", c_int),
                        ("y", c_int)]
        mod.tagpoint = tagpoint
        mod.byref = byref


class Test_rctypes:

    def test_simple(self):
        res = o_atoi('42')   
        assert res == 42 

    def test_annotate_simple(self):
        a = RPythonAnnotator()
        s = a.build_types(o_atoi, [str])
        # result should be an integer
        assert s.knowntype == int

    def test_specialize_simple(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(o_atoi, [str])
        # result should be an integer
        assert s.knowntype == int
        t.buildrtyper().specialize()
        #d#t.view()

    def test_compile_simple(self):
        fn = compile(o_atoi, [str])
        res = fn("42")
        assert res == 42


class Test_structure:

    def setup_class(cls):
        compile_c_module([py.path.local("_rctypes_test.c")], "_rctypes_test")

    def test_simple_as_extension_module(self):
        import _rctypes_test as t0
        import _rctypes_test as t1
        assert t1 is t0
        assert "_rctypes_test" in sys.modules

    def test_simple(self):
        if sys.platform == "win32":
            dll = cdll.LoadLibrary("_rctypes_test.pyd")
        else:
            dll = cdll.LoadLibrary("_rctypes_test.so")
        in_point = tagpoint()
        in_point.x = 42
        in_point.y = 17
        out_point = tagpoint()
        assert in_point.x + in_point.y == dll._testfunc_byval(in_point, byref(out_point))
        assert out_point.x == 42
        assert out_point.y == 17


