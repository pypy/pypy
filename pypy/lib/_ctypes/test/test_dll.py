import ctypes

def test_dll_simple():
    dll = ctypes.cdll.LoadLibrary("libm.so.6")
    sin = dll.sin
    sin.argtypes = [ctypes.c_double]
    sin.restype = ctypes.c_double
    assert sin(0) == 0
