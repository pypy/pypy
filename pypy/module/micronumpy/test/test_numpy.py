
from pypy.conftest import gettestobjspace

class AppTestNumpy(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))
    
    def test_zeroes(self):
        from numpy import zeros
        ar = zeros(3, dtype=int)
        assert ar[0] == 0
    
    def test_setitem_getitem(self):
        from numpy import zeros
        ar = zeros(8, dtype=int)
        assert ar[0] == 0
        ar[1] = 3
        assert ar[1] == 3
        raises((TypeError, ValueError), ar.__getitem__, 'xyz')
        raises(IndexError, ar.__getitem__, 38)
        assert ar[-2] == 0
        assert ar[-7] == 3
        assert len(ar) == 8
