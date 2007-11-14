
from pypy.conftest import gettestobjspace
import sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestCtypes:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ffi','struct'))

    def test_rand(self):
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        rand = libc.rand
        first = rand()
        counter = 0
        for i in range(100):
            next = rand()
            if next == first:
                counter += 1
        assert counter < 100

