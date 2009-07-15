
from pypy.conftest import gettestobjspace

class AppTestNumpy(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))
    
    def test_zeroes(self):
        from numpy import zeros
        ar = zeros(3, dtype=int)
        assert ar[0] == 0
    
