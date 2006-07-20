from pypy.conftest import gettestobjspace
from py.test import skip


class AppTest_ComputationSpace(object):
    skip("currently unplugged")
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic', usemodules=('_stackless', ))

    def test_instantiate(self):
        cspace = newspace()
        assert str(type(cspace)) == "<type 'W_ComputationSpace'>"

    def test_var(self):
        cspace = newspace()
        v = cspace.var("foo", FiniteDomain([1,2,3]))
        assert str(v).startswith('<W_Variable object at')
        raises(Exception, cspace.var, "foo", FiniteDomain([1,2,3]))

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
        for v in (v1, v2):
            assert cstr in csp.dependant_constraints(v)

    def test_propagate(self):
        csp = newspace()
        x = csp.var('x', FiniteDomain([1]))
        y = csp.var('y', FiniteDomain([1, 2]))
        z = csp.var('z', FiniteDomain([1, 2, 3]))
        csp.tell(make_expression([x, y], 'x<y'))
        csp.tell(make_expression([y, z], 'y<z'))
        csp.tell(make_expression([x, z], 'x<z'))
        csp.ask() #just call propagate for now
        assert csp.dom(x) == FiniteDomain([1])
        assert csp.dom(y) == FiniteDomain([2])
        assert csp.dom(z) == FiniteDomain([3])

    def test_clone(self):
        csp = newspace()
        x = csp.var('x', FiniteDomain([1]))
        y = csp.var('y', FiniteDomain([1, 2]))
        z = csp.var('z', FiniteDomain([1, 2, 3]))
        csp.tell(make_expression([x, y], 'x<y'))
        csp.tell(make_expression([y, z], 'y<z'))
        csp.tell(make_expression([x, z], 'x<z'))
        new = csp.clone()
        new.ask()
        assert new.dom(x) == FiniteDomain([1])
        assert new.dom(y) == FiniteDomain([2])
        assert new.dom(z) == FiniteDomain([3])
        assert csp.dom(x) == FiniteDomain([1])
        assert csp.dom(y) == FiniteDomain([1, 2])
        assert csp.dom(z) == FiniteDomain([1, 2, 3])
        
    def test_commit(self):
        # using default (dichotomy) distributor
        csp = newspace()
        x = csp.var('x', FiniteDomain([1]))
        y = csp.var('y', FiniteDomain([1, 2]))
        z = csp.var('z', FiniteDomain([1, 2, 3, 4]))
        csp.tell(make_expression([x, y], 'x<y'))
        csp.tell(make_expression([y, z], 'y<z'))
        csp.tell(make_expression([x, z], 'x<z'))
        csp.commit(2)
        assert csp.dom(y).size() == 1
        csp.commit(2)
        assert csp.dom(z).size() == 2

    def test_ask_success(self):
        csp = newspace()
        x = csp.var('x', FiniteDomain([1]))
        y = csp.var('y', FiniteDomain([1, 2]))
        z = csp.var('z', FiniteDomain([1, 2, 3]))
        csp.tell(make_expression([x, y], 'x<y'))
        csp.tell(make_expression([y, z], 'y<z'))
        csp.tell(make_expression([x, z], 'x<z'))
        assert csp.ask() == 1
        
    def test_ask_failure(self):
        csp = newspace()
        x = csp.var('x', FiniteDomain([1]))
        y = csp.var('y', FiniteDomain([1, 2]))
        z = csp.var('z', FiniteDomain([1, 2]))
        csp.tell(make_expression([x, y], 'x<y'))
        csp.tell(make_expression([y, z], 'y<z'))
        csp.tell(make_expression([x, z], 'x<z'))
        assert csp.ask() == 0

    def test_ask_distributable(self):
        csp = newspace()
        x = csp.var('x', FiniteDomain([1, 2]))
        y = csp.var('y', FiniteDomain([2, 3]))
        z = csp.var('z', FiniteDomain([3, 4]))
        csp.tell(make_expression([x, y], 'x<y'))
        csp.tell(make_expression([y, z], 'y<z'))
        csp.tell(make_expression([x, z], 'x<z'))
        assert csp.ask() > 1

    def test_merge(self):
        csp = newspace()
        def problem(csp):
            x = csp.var('x', FiniteDomain([1]))
            y = csp.var('y', FiniteDomain([1, 2]))
            z = csp.var('z', FiniteDomain([1, 2, 3]))
            csp.tell(make_expression([x, y], 'x<y'))
            csp.tell(make_expression([y, z], 'y<z'))
            csp.tell(make_expression([x, z], 'x<z'))
            return [x, y, z]
        csp.define_problem(problem)
        assert csp.ask() == 1
        assert csp.merge() == (1, 2, 3)

    def test_clone_and_merge(self):
        csp = newspace()
        def problem(csp):
            x = csp.var('x', FiniteDomain([1]))
            y = csp.var('y', FiniteDomain([1, 2]))
            z = csp.var('z', FiniteDomain([1, 2, 3]))
            csp.tell(AllDistinct([x, y, z]))
            return [x, y, z]
        csp.define_problem(problem)
        csp = csp.clone()
        assert csp.ask() == 1
        assert csp.merge() == (1, 2, 3)
