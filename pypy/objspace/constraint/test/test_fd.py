from pypy.conftest import gettestobjspace

class UnificationFailure(Exception):  pass

class AppTest_FD(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_instantiate(self):
        fd = FiniteDomain([1, 2, 3])
        assert fd.size() == 3
        assert set(fd.get_values()) == set([1, 2, 3])
        #fd2 = fd.copy()
