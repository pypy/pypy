import unification as u
import variable as v
import constraint as c
import computationspace as cs
import distributor as di
from py.test import raises

def satisfiable_problem(computation_space):
    cs = computation_space
    s = cs.store 
    x, y, z, w = (s.var('x'), s.var('y'),
                  s.var('z'), s.var('w'))
    s.set_domain(x, c.FiniteDomain([2, 6]))
    s.set_domain(y, c.FiniteDomain([2, 3]))
    s.set_domain(z, c.FiniteDomain([4, 5]))
    s.set_domain(w, c.FiniteDomain([1, 4, 5, 6, 7]))
    s.add_constraint(c.Expression([x, y, z], 'x == y + z'))
    s.add_constraint(c.Expression([z, w], 'z < w'))
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor())
    return (x, w, y)

def unsatisfiable_problem(computation_space):
    cs = computation_space
    s = cs.store 
    x, y, z, w = (s.var('x'), s.var('y'),
                  s.var('z'), s.var('w'))
    s.set_domain(x, c.FiniteDomain([2, 6]))
    s.set_domain(y, c.FiniteDomain([2, 3]))
    s.set_domain(z, c.FiniteDomain([4, 5]))
    s.set_domain(w, c.FiniteDomain([1]))
    s.add_constraint(c.Expression([x, y, z], 'x == y + z'))
    s.add_constraint(c.Expression([z, w], 'z < w'))
    # set up a distribution strategy
    cs.set_distributor(di.DichotomyDistributor())
    return (x, w, y)


class TestComputationSpace:

    def setup_method(self, meth):
        pass

    def test_bind_cs_root(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        assert 'root' in spc.store.names
        assert set(['x', 'y', 'w']) == \
               set([var.name for var in spc.root.val])

    def test_process_and_ask_success(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        assert spc.ask() == cs.Unprocessed
        spc.process()
        assert spc.ask() == cs.Succeeded
        

    def test_process_and_ask_failure(self):
        spc = cs.ComputationSpace(unsatisfiable_problem)
        assert spc.ask() == cs.Unprocessed
        spc.process()
        assert spc.ask() == cs.Failed

    def test_distribute(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        spc.process()
        domains = dict([(var, var.dom) for var in spc.store.vars
                        if var.dom])
        new_domains = spc.distributor.distribute(domains)
        x, y, z, w = (spc.store.get_var_by_name('x'),
                      spc.store.get_var_by_name('y'),
                      spc.store.get_var_by_name('z'),
                      spc.store.get_var_by_name('w'))
        assert new_domains == [{x: c.FiniteDomain([6]),
                                y: c.FiniteDomain([2]),
                                z: c.FiniteDomain([4]),
                                w: c.FiniteDomain([5])},
                               {x: c.FiniteDomain([6]),
                                y: c.FiniteDomain([2]),
                                z: c.FiniteDomain([4]),
                                w: c.FiniteDomain([6, 7])}]
                               
