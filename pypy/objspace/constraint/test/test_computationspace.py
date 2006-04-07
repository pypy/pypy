from pypy.conftest import gettestobjspace


class AppTest_ComputationSpace(object):
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_instantiate(self):
        cspace = newspace()
        assert str(type(cspace)) == "<type 'W_ComputationSpace'>"

    def test_var(self):
        cspace = newspace()
        v = cspace.var("foo", FiniteDomain([1,2,3]))
        assert str(v).startswith('<W_Variable object at')
        #FIXME: raise the good exc. type
        raises(Exception, cspace.var, "foo", FiniteDomain([1,2,3]))
    


