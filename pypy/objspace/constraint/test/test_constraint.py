from pypy.conftest import gettestobjspace

class AppTest_AllDistinct(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

        
    def test_instantiate(self):
        cspace = newspace()
        v1 = cspace.var('v1', FiniteDomain([1,2]))
        v2 = cspace.var('v2', FiniteDomain([1,2]))
        cstr = AllDistinct([v1, v2])
        variables = cstr.affected_variables()
        assert variables is not None
        assert len(variables) == 2
        assert v1 in variables
        assert v2 in variables

    def test_estimated_cost(self):
        csp = newspace()
        v1 = csp.var('v1', FiniteDomain([1, 2]))
        v2 = csp.var('v2', FiniteDomain([1, 2]))
        cstr = AllDistinct([v1, v2])
        assert cstr.estimate_cost(csp) == 1

    def notest_repr(self):
        csp = newspace()
        v1 = csp.var('v1', FiniteDomain([1, 2]))
        v2 = csp.var('v2', FiniteDomain([1, 2]))
        cstr = AllDistinct([v1, v2])
        print cstr

    def test_revise(self):
        csp = newspace()
        v1 = csp.var('v1', FiniteDomain([1, 2]))
        v2 = csp.var('v2', FiniteDomain([1, 2]))
        cstr = AllDistinct([v1, v2])
        assert cstr.revise(csp) == 0 # not entailed

        v3 = csp.var('v3', FiniteDomain([1]))
        v4 = csp.var('v4', FiniteDomain([2]))
        cstr = AllDistinct([v3, v4])
        assert cstr.revise(csp) == 1 # entailed

        v5 = csp.var('v5', FiniteDomain([1]))
        v6 = csp.var('v6', FiniteDomain([1]))
        cstr = AllDistinct([v5, v6])
        raises(Exception, cstr.revise, csp)

        v7 = csp.var('v7', FiniteDomain([1, 2]))
        v8 = csp.var('v8', FiniteDomain([1, 2]))
        cstr = AllDistinct([v2, v7, v8])
        raises(Exception, cstr.revise, csp)

        v9 = csp.var('v9', FiniteDomain([1]))
        v10= csp.var('v10', FiniteDomain([1,2]))
        cstr = AllDistinct([v9, v10])
        assert cstr.revise(csp) == 1
        assert csp.dom(v10).get_values() == [2]

