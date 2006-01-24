import py.test
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile
    

def setup_module(mod):
    try:
        import ctypes
    except ImportError:
        py.test.skip("this test needs ctypes installed")
    else:
        import sys
        from pypy.rpython.rctypes.interface import cdll, c_char_p, c_int, c_char, POINTER
        if sys.platform == 'win32':
            mylib = cdll.LoadLibrary('msvcrt.dll')
        elif sys.platform == 'linux2':
            mylib = cdll.LoadLibrary('libc.so.6')
        else:
            py.test.skip("don't know how to load the c lib for %s" % 
                    sys.platform)

        atoi = mylib.atoi
        atoi.restype = c_int
        atoi.argstype = [c_char_p]
        atoi.argstype = [POINTER(c_char)]
        def o_atoi(a):
           return atoi(a)
        mod.o_atoi = o_atoi


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

    def x_test_compile_simple(self):
        fn = compile(o_atoi, [str])
        res = fn("42")
        assert res == 42

