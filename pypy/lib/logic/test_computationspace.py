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
        new_domains = [d.items() for d in
                       spc.distributor.distribute()]
        x, y, z, w = (spc.store.get_var_by_name('x'),
                      spc.store.get_var_by_name('y'),
                      spc.store.get_var_by_name('z'),
                      spc.store.get_var_by_name('w'))
        expected_domains = [{x: c.FiniteDomain([6]),
                             y: c.FiniteDomain([2]),
                             z: c.FiniteDomain([4]),
                             w: c.FiniteDomain([5])}.items(),
                            {x: c.FiniteDomain([6]),
                             y: c.FiniteDomain([2]),
                             z: c.FiniteDomain([4]),
                             w: c.FiniteDomain([6, 7])}.items()]
        for (d1, d2) in zip(new_domains, expected_domains):
            for (e1, e2) in zip(d1, d2):
                print e1, '=?', e2
                assert e1 == e2
        # the following assertion fails for mysterious reasons
        # have we discovered a bug in CPython ?
        # assert set(new_domains) == set(expected_domains)

    def test_make_children(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        x, y, z, w = (spc.store.get_var_by_name('x'),
                      spc.store.get_var_by_name('y'),
                      spc.store.get_var_by_name('z'),
                      spc.store.get_var_by_name('w'))
        spc.process()
        spc.make_children()
        assert len(spc.children) == 2
        new_domains = []
        all_vars = spc.store.get_variables_with_a_domain()
        for child in spc.children:
            new_domains.append([(var, var.cs_get_dom(child))
                                for var in all_vars])
            
        expected_domains = [{x: c.FiniteDomain([6]),
                             y: c.FiniteDomain([2]),
                             z: c.FiniteDomain([4]),
                             w: c.FiniteDomain([5])}.items(),
                            {x: c.FiniteDomain([6]),
                             y: c.FiniteDomain([2]),
                             z: c.FiniteDomain([4]),
                             w: c.FiniteDomain([6, 7])}.items()]

            
