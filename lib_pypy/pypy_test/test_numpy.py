from pypy.conftest import gettestobjspace

class AppTestNumPyModule:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_numpy'])

    def test_mean(self):
        from numpy import array, mean
        assert mean(array(range(5))) == 2.0
        assert mean(range(5)) == 2.0

    def test_average(self):
        from numpy import array, average
        assert average(range(10)) == 4.5
        assert average(array(range(10))) == 4.5
