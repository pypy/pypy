import py.test

def setup_module(mod):
    try:
        import ctypes
    except ImportError:
        py.test.skip("this test needs ctypes installed")

class Test_rctypes:
    def test_simple(self):
        from pypy.rpython.rctypes.interface import windll, c_char_p

        import sys
        if sys.platform == 'win32':
            py.test.raises(WindowsError,"windll.LoadLibrary('kernel42.dll')")
            mylib = windll.LoadLibrary('kernel32.dll')
            gcl = mylib.GetCommandLineA
            gcl.restype = c_char_p
            def tst():
               return gcl()
            res = tst()   
            assert isinstance(res, str)
