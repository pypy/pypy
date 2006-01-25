import unification as u
import variable as v
import constraint as c
import computationspace as cs
from py.test import raises


class TestComputationSpace:

    def setUp(self):
        pass

    def test_bind_cs_root(self):

        def dummy_problem(store):
            s = store # i'm lazy
            x, y, z, w = (s.var('x'), s.var('y'),
                          s.var('z'), s.var('w'))
            s.set_domain(x, c.FiniteDomain([2, 6]))
            s.set_domain(y, c.FiniteDomain([2, 3]))
            s.set_domain(z, c.FiniteDomain([4, 5]))
            s.set_domain(w, c.FiniteDomain([1, 4, 5]))
            s.add_constraint(c.Expression([x, y, z], 'x == y + z'))
            s.add_constraint(c.Expression([z, w], 'z < w'))
            # we don't know yet how to
            # set up a distribution strategy
            return (x, y, z) 

        spc = cs.ComputationSpace(dummy_problem)
        assert 'root' in spc.store.names
        assert ['x', 'y', 'z'] == [var.name for var
                                   in spc.root.val]
