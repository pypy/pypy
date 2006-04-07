from pypy.conftest import gettestobjspace

class AppTest_AllDistinct(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

        
    def test_instantiate(self):
        cspace = newspace()
        v1 = cspace.var('v1', FiniteDomain([1,2]))
        v2 = cspace.var('v2', FiniteDomain([1,2]))
        cstr = AllDistinct(cspace, [v1, v2])
        variables = cstr.affected_variables()
        assert variables is not None
        print variables
        assert len(variables) == 2
        assert v1 in variables
        assert v2 in variables
