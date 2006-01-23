import py.test

def setup_module(mod):
    try:
        import ctypes
    except ImportError:
        py.test.skip("this test needs ctypes installed")

class Test_rctypes:
    def test_simple(self):
        from pypy.rpython.rctypes.interface import cdll, c_char_p, c_int

        import sys
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
        def o_atoi(a):
           return atoi(a)

        res = o_atoi('42')   
        assert res == 42 
