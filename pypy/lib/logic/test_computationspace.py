from threading import Thread

import variable as v
import constraint as c
import computationspace as cs
import distributor as di
from problems import *
from py.test import raises


#-- meat ------------------------

class FunThread(Thread):

    def __init__(self, fun, *args):
        Thread.__init__(self)
        self.fun = fun
        self.args = args

    def run(self):
        self.fun(self, *self.args)

class TestStoreUnification:
    
    def setup_method(self, meth):
        cs._cs = cs.ComputationSpace(dummy_problem)

    def test_already_in_store(self):
        x = cs.var('x')
        raises(v.AlreadyInStore, cs.var, 'x')

    def test_already_bound(self):
        x = cs.var('x')
        cs.bind(x, 42)
        raises(cs.AlreadyBound, cs.bind, x, 42)

    def test_bind_var_var(self):
        x = cs.var('x')
        y = cs.var('y')
        z = cs.var('z')
        cs.bind(x, z)
        assert x.val == cs.EqSet([x, z])
        assert y.val == cs.EqSet([y])
        assert z.val == cs.EqSet([x, z])

    def test_bind_var_val(self):
        x, y, z = cs.var('x'), cs.var('y'), cs.var('z')
        cs.bind(x, z)
        cs.bind(y, 42)
        cs.bind(z, 3.14)
        assert x.val == 3.14
        assert y.val == 42
        assert z.val == 3.14

    def test_unify_same(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        cs.bind(x, [42, z])
        cs.bind(y, [z, 42])
        cs.bind(w, [z, 43])
        raises(cs.UnificationFailure, cs.unify, x, w)
        cs.unify(x, y)
        assert z.val == 42

    def test_double_unification(self):
        x, y, z = (cs.var('x'), cs.var('y'),
                   cs.var('z'))
        cs.bind(x, 42)
        cs.bind(y, z)
        cs.unify(x, y)
        assert z.val == 42
        cs.unify(x, y)
        assert (z.val == x.val) and (x.val == y.val)


    def test_unify_values(self):
        x, y = cs.var('x'), cs.var('y')
        cs.bind(x, [1, 2, 3])
        cs.bind(y, [1, 2, 3])
        cs.unify(x, y)
        assert x.val == [1, 2, 3]
        assert y.val == [1, 2, 3]

    def test_unify_lists_success(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        cs.bind(x, [42, z])
        cs.bind(y, [w, 44])
        cs.unify(x, y)
        assert x.val == [42, z]
        assert y.val == [w, 44]
        assert z.val == 44
        assert w.val == 42

    def test_unify_dicts_success(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        cs.bind(x, {1:42, 2:z})
        cs.bind(y, {1:w,  2:44})
        cs.unify(x, y)
        assert x.val == {1:42, 2:z}
        assert y.val == {1:w,  2:44}
        assert z.val == 44
        assert w.val == 42

    def test_unify_failure(self):
        x,y,z = cs.var('x'), cs.var('y'), cs.var('z')
        cs.bind(x, [42, z])
        cs.bind(y, [z, 44])
        raises(cs.UnificationFailure, cs.unify, x, y)
        # check store consistency
        assert x.val == [42, z]
        assert y.val == [z, 44]
        assert z.val == cs.EqSet([z])

    def test_unify_failure2(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        cs.bind(x, [42, z])
        cs.bind(y, [w, 44])
        cs.bind(z, w)
        assert cs._cs.in_transaction == False
        raises(cs.UnificationFailure, cs.unify, x, y)
        assert cs._cs.in_transaction == False
        # check store consistency
        assert x.val == [42, z]
        assert y.val == [w, 44]
        assert z.val == cs.EqSet([z,w])
        assert w.val == cs.EqSet([z,w])

    def test_unify_circular(self):
        x, y, z, w, a, b = (cs.var('x'), cs.var('y'),
                            cs.var('z'), cs.var('w'),
                            cs.var('a'), cs.var('b'))
        cs.bind(x, [y])
        cs.bind(y, [x])
        raises(cs.UnificationFailure, cs.unify, x, y)
        cs.bind(z, [1, w])
        cs.bind(w, [z, 2])
        raises(cs.UnificationFailure, cs.unify, z, w)
        cs.bind(a, {1:42, 2:b})
        cs.bind(b, {1:a,  2:42})
        raises(cs.UnificationFailure, cs.unify, a, b)
        # check store consistency
        assert x.val == [y]
        assert y.val == [x]
        assert z.val == [1, w]
        assert w.val == [z, 2]
        assert a.val == {1:42, 2:b}
        assert b.val == {1:a,  2:42}
        
        
    def test_threads_creating_vars(self):
        def create_var(thread, *args):
            x = cs.var('x')

        def create_var2(thread, *args):
            raises(v.AlreadyExists, cs.var, 'x')

        t1, t2 = (FunThread(create_var),
                  FunThread(create_var2))
        t1.start()
        t2.start()


    def test_threads_binding_vars(self):

        def do_stuff(thread, var, val):
            thread.raised = False
            try:
                # pb. with TLS (thread-local-stuff) in
                # cs class
                cs.bind(var, val)
            except Exception, e:
                print e
                thread.raised = True
                assert isinstance(e, cs.AlreadyBound)
            
        x = cs.var('x')
        vars_ = []
        for nvar in range(1000):
            v = cs.var('x-'+str(nvar))
            cs.bind(x, v)
            vars_.append(v)
            
        for var in vars_:
            assert var in cs._cs.vars
            assert var.val == x.val

        t1, t2 = (FunThread(do_stuff, x, 42),
                  FunThread(do_stuff, x, 43))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        #check that every var is really bound to 42 or 43
        for var in vars_:
            assert var in cs._cs.vars
            assert var.val == x.val
        assert (t2.raised and not t1.raised) or \
               (t1.raised and not t2.raised)
    

    def test_set_var_domain(self):
        x = cs.var('x')
        cs.set_domain(x, [1, 3, 5])
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 3, 5])

    def test_bind_with_domain(self):
        x = cs.var('x')
        cs.set_domain(x, [1, 2, 3])
        raises(cs.OutOfDomain, cs.bind, x, 42)
        cs.bind(x, 3)
        assert x.val == 3

    def test_bind_with_incompatible_domains(self):
        x, y = cs.var('x'), cs.var('y')
        cs.set_domain(x, [1, 2])
        cs.set_domain(y, [3, 4])
        raises(cs.IncompatibleDomains, cs.bind, x, y)
        cs.set_domain(y, [2, 4])
        cs.bind(x, y)
        # check x and y are in the same equiv. set
        assert x.val == y.val


    def test_unify_with_domains(self):
        x,y,z = cs.var('x'), cs.var('y'), cs.var('z')
        cs.bind(x, [42, z])
        cs.bind(y, [z, 42])
        cs.set_domain(z, [1, 2, 3])
        raises(cs.UnificationFailure, cs.unify, x, y)
        cs.set_domain(z, [41, 42, 43])
        cs.unify(x, y)
        assert z.val == 42
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([41, 42, 43])

    def test_add_constraint(self):
        x,y,z = cs.var('x'), cs.var('y'), cs.var('z')
        raises(c.DomainlessVariables,
               c.Expression, cs._cs, [x, y, z], 'x == y + z')
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        k = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        cs.add_constraint(k)
        assert k in cs._cs.constraints

    def test_narrowing_domains_failure(self):
        x,y,z = cs.var('x'), cs.var('y'), cs.var('z')
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        k = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        raises(c.ConsistencyFailure, k.narrow)

    def test_narrowing_domains_success(self):
        x,y,z = cs.var('x'), cs.var('y'), cs.var('z')
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        k = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        k.narrow()
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3])

    def test_compute_dependant_vars(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        w.cs_set_dom(cs._cs, c.FiniteDomain([1, 4, 5]))
        k1 = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        k2 = c.Expression(cs._cs, [z, w], 'z < w')
        cs.add_constraint(k1)
        cs.add_constraint(k2)
        varset = set()
        constset = set()
        cs._cs._compute_dependant_vars(k1, varset, constset)
        assert varset == set([x, y, z, w])
        assert constset == set([k1, k2])

    def test_store_satisfiable_success(self):
        x,y,z = cs.var('x'), cs.var('y'), cs.var('z')
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        k = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        cs.add_constraint(k)
        assert cs.satisfiable(k) == True
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])
        
    def test_store_satisfiable_failure(self):
        x,y,z = cs.var('x'), cs.var('y'), cs.var('z')
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        k = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        cs.add_constraint(k)
        assert cs.satisfiable(k) == False
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])

    def test_satisfiable_many_const_success(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        w.cs_set_dom(cs._cs, c.FiniteDomain([1, 4, 5]))
        k1 = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        k2 = c.Expression(cs._cs, [z, w], 'z < w')
        cs.add_constraint(k1)
        cs.add_constraint(k2)
        assert cs.satisfiable(k1) == True
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(cs._cs) == c.FiniteDomain([1, 4, 5])
        assert cs.satisfiable(k2) == True
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(cs._cs) == c.FiniteDomain([1, 4, 5])
        narrowed_doms = cs.get_satisfying_domains(k1)
        assert narrowed_doms == {x:c.FiniteDomain([5]),
                                 y:c.FiniteDomain([2]),
                                 z:c.FiniteDomain([3]),
                                 w:c.FiniteDomain([4, 5])}
        narrowed_doms = cs.get_satisfying_domains(k2)
        assert narrowed_doms == {x:c.FiniteDomain([5]),
                                 y:c.FiniteDomain([2]),
                                 z:c.FiniteDomain([3]),
                                 w:c.FiniteDomain([4, 5])}


    def test_satisfiable_many_const_failure(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        w.cs_set_dom(cs._cs, c.FiniteDomain([1]))
        k1 = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        k2 = c.Expression(cs._cs, [z, w], 'z < w')
        cs.add_constraint(k1)
        cs.add_constraint(k2)
        assert cs.satisfiable(k1) == False
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(cs._cs) == c.FiniteDomain([1])
        assert cs.satisfiable(k2) == False
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(cs._cs) == c.FiniteDomain([1])
        narrowed_doms = cs.get_satisfying_domains(k1)
        assert narrowed_doms == {}
        narrowed_doms = cs.get_satisfying_domains(k2)
        assert narrowed_doms == {}

    def test_satisfy_many_const_failure(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        w.cs_set_dom(cs._cs, c.FiniteDomain([1]))
        k1 = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        k2 = c.Expression(cs._cs, [z, w], 'z < w')
        cs.add_constraint(k1)
        cs.add_constraint(k2)
        raises(cs.ConsistencyFailure, cs.satisfy, k1)
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(cs._cs) == c.FiniteDomain([1])
        raises(cs.ConsistencyFailure, cs.satisfy, k2)
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(cs._cs) == c.FiniteDomain([1])
        
    def test_satisfy_many_const_success(self):
        x,y,z,w = (cs.var('x'), cs.var('y'),
                   cs.var('z'), cs.var('w'))
        x.cs_set_dom(cs._cs, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(cs._cs, c.FiniteDomain([2, 3]))
        z.cs_set_dom(cs._cs, c.FiniteDomain([3, 4]))
        w.cs_set_dom(cs._cs, c.FiniteDomain([1, 4, 5]))
        k1 = c.Expression(cs._cs, [x, y, z], 'x == y + z')
        k2 = c.Expression(cs._cs, [z, w], 'z < w')
        cs.add_constraint(k1)
        cs.add_constraint(k2)
        cs.satisfy(k2)
        print x.cs_get_dom(cs._cs)
        assert x.cs_get_dom(cs._cs) == c.FiniteDomain([5])
        assert y.cs_get_dom(cs._cs) == c.FiniteDomain([2])
        assert z.cs_get_dom(cs._cs) == c.FiniteDomain([3])
        assert w.cs_get_dom(cs._cs) == c.FiniteDomain([4, 5])


class TestComputationSpace:

    def setup_method(self, meth):
        pass

    def test_bind_cs_root(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        assert '__root__' in spc.names
        assert set(['x', 'y', 'w']) == \
               set([var.name for var in spc.root.val])

    def test_ask_success(self):
        spc = cs.ComputationSpace(one_solution_problem)
        assert spc.ask() == cs.Succeeded

    def test_double_ask(self):
        spc = cs.ComputationSpace(one_solution_problem)
        assert spc.ask() == cs.Succeeded
        assert spc.ask() == cs.Succeeded
        
    def test_ask_failure(self):
        spc = cs.ComputationSpace(unsatisfiable_problem)
        assert spc.ask() == cs.Failed

    def test_ask_alternatives(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        assert spc.ask() == cs.Alternatives(2)

    def test_distribute(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        new_domains = [tuple(d.items()) for d in
                       spc.distributor.distribute()]
        x, y, z, w = (spc.get_var_by_name('x'),
                      spc.get_var_by_name('y'),
                      spc.get_var_by_name('z'),
                      spc.get_var_by_name('w'))
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

    def test_clone(self):
        spc = cs.ComputationSpace(satisfiable_problem)
        w = spc.get_var_by_name('w')
        assert spc.ask() == cs.Alternatives(2)
        new_spc = spc.clone()
        new_spc.add_constraint(c.Expression(new_spc, [w], 'w == 5'))
        new_spc._process()
        assert spc.ask() == cs.Alternatives(2)
        assert new_spc.ask() == cs.Succeeded
        assert w.cs_get_dom(spc) == c.FiniteDomain([5, 6, 7])
        assert w.cs_get_dom(new_spc) == c.FiniteDomain([5])
        spc.commit(0)
        new_spc.commit(0)
