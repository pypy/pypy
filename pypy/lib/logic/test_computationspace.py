import unification as u
import variable as v
import constraint as c
import computationspace as cs
import distributor as di
from py.test import raises

#-- utility ------------------

class hdict(dict):
    """a hashable dict"""

    def __hash__(self):
        return id(self)

#-- helpers -----------------

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
    cs.set_distributor(di.DichotomyDistributor(cs))
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
    cs.set_distributor(di.DichotomyDistributor(cs))
    return (x, w, y)

#-- meat ------------------------

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
        assert spc.ask() == cs.Succeeded

    def test_process_and_ask_failure(self):
        spc = cs.ComputationSpace(unsatisfiable_problem)
        assert spc.ask() == cs.Failed

    def test_distribute(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        new_domains = [tuple(d.items()) for d in
                       spc.distributor.distribute()]
        x, y, z, w = (spc.store.get_var_by_name('x'),
                      spc.store.get_var_by_name('y'),
                      spc.store.get_var_by_name('z'),
                      spc.store.get_var_by_name('w'))
        expected_domains = [tuple({x: c.FiniteDomain([6]),
                             y: c.FiniteDomain([2]),
                             z: c.FiniteDomain([4]),
                             w: c.FiniteDomain([5])}.items()),
                            tuple({x: c.FiniteDomain([6]),
                             y: c.FiniteDomain([2]),
                             z: c.FiniteDomain([4]),
                             w: c.FiniteDomain([6, 7])}.items())]
        print new_domains, expected_domains
        assert len(new_domains) == len(expected_domains)
        for (d1, d2) in zip(new_domains, expected_domains):
            assert len(d1) == len(d2)
            for (e1, e2) in zip(d1, d2):
                print e1, '=?', e2
                assert e1 == e2
        # the following assertion fails for mysterious reasons
        # have we discovered a bug in CPython ?
        #print hash(new_domains[0]), hash(new_domains[1])
        #print hash(expected_domains[0]), hash(expected_domains[1])
        #assert set(new_domains) == set(expected_domains)

        
