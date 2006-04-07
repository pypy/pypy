from pypy.conftest import gettestobjspace


class AppTest_ComputationSpace(object):
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_instantiate(self):
        cspace = newspace()
        assert str(type(cspace)) == "<type 'W_ComputationSpace'>"

    def test_var(self):
        cspace = newspace()
        cspace.var("foo", FiniteDomain([1,2,3]))

    


