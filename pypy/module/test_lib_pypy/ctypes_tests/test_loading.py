from ctypes import CDLL
from ctypes.util import find_library

class TestLoader:

    def test__handle(self):
        lib = find_library("c")
        if lib:
            cdll = CDLL(lib)
            assert type(cdll._handle) in (int, long)
