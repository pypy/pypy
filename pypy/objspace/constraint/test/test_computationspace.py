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
        v = cspace.var("foo", FiniteDomain([1,2,3]))
        assert str(v).startswith('<W_Variable object at')

    def test_dom(self):
        cspace = newspace()
        domain = FiniteDomain([1,2,3])
        v = cspace.var("foo", domain)
        assert cspace.dom(v) is domain

    def test_tell(self):
        csp = newspace()
        v1 = csp.var('v1', FiniteDomain([1, 2]))
        v2 = csp.var('v2', FiniteDomain([1, 2]))
        cstr = AllDistinct([v1, v2])
        csp.tell(cstr)

    def test_propagate(self):
        csp = newspace()
        x = csp.var('x', FiniteDomain([1]))
        y = csp.var('y', FiniteDomain([1, 2]))
        z = csp.var('z', FiniteDomain([1, 2, 3]))
        csp.tell(make_expression([x, y], 'x<y'))
        csp.tell(make_expression([y, z], 'y<z'))
        csp.tell(make_expression([x, z], 'x<z'))
        csp.propagate()
        assert csp.dom(x) == FiniteDomain([1])
        assert csp.dom(y) == FiniteDomain([2])
        assert csp.dom(z) == FiniteDomain([3])
        
