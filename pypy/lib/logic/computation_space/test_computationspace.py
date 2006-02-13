from threading import Thread

import variable as v
import constraint as c
import computationspace as space
import distributor as di
import problems
from py.test import raises

#-- utility ---------------------

class FunThread(Thread):

    def __init__(self, fun, *args):
        Thread.__init__(self)
        self.fun = fun
        self.args = args

    def run(self):
        self.fun(self, *self.args)

#-- meat ------------------------

class TestStoreUnification:
    

    def test_already_in_store(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x = sp.var('x')
        raises(v.AlreadyInStore, sp.var, 'x')

    def test_already_bound(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x = sp.var('x')
        sp.bind(x, 42)
        raises(space.AlreadyBound, sp.bind, x, 42)

    def test_bind_var_var(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x = sp.var('x')
        y = sp.var('y')
        z = sp.var('z')
        sp.bind(x, z)
        assert x.val == space.EqSet([x, z])
        assert y.val == space.EqSet([y])
        assert z.val == space.EqSet([x, z])

    def test_bind_var_val(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x, y, z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.bind(x, z)
        sp.bind(y, 42)
        sp.bind(z, 3.14)
        assert x.val == 3.14
        assert y.val == 42
        assert z.val == 3.14

    def test_unify_same(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        sp.bind(x, [42, z])
        sp.bind(y, [z, 42])
        sp.bind(w, [z, 43])
        raises(space.UnificationFailure, sp.unify, x, w)
        sp.unify(x, y)
        assert z.val == 42

    def test_double_unification(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x, y, z = (sp.var('x'), sp.var('y'),
                   sp.var('z'))
        sp.bind(x, 42)
        sp.bind(y, z)
        sp.unify(x, y)
        assert z.val == 42
        sp.unify(x, y)
        assert (z.val == x.val) and (x.val == y.val)


    def test_unify_values(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x, y = sp.var('x'), sp.var('y')
        sp.bind(x, [1, 2, 3])
        sp.bind(y, [1, 2, 3])
        sp.unify(x, y)
        assert x.val == [1, 2, 3]
        assert y.val == [1, 2, 3]

    def test_unify_lists_success(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        sp.bind(x, [42, z])
        sp.bind(y, [w, 44])
        sp.unify(x, y)
        assert x.val == [42, z]
        assert y.val == [w, 44]
        assert z.val == 44
        assert w.val == 42

    def test_unify_dicts_success(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        sp.bind(x, {1:42, 2:z})
        sp.bind(y, {1:w,  2:44})
        sp.unify(x, y)
        assert x.val == {1:42, 2:z}
        assert y.val == {1:w,  2:44}
        assert z.val == 44
        assert w.val == 42

    def test_unify_failure(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.bind(x, [42, z])
        sp.bind(y, [z, 44])
        raises(space.UnificationFailure, sp.unify, x, y)
        # check store consistency
        assert x.val == [42, z]
        assert y.val == [z, 44]
        assert z.val == space.EqSet([z])

    def test_unify_failure2(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        sp.bind(x, [42, z])
        sp.bind(y, [w, 44])
        sp.bind(z, w)
        assert sp.in_transaction == False
        raises(space.UnificationFailure, sp.unify, x, y)
        assert sp.in_transaction == False
        # check store consistency
        assert x.val == [42, z]
        assert y.val == [w, 44]
        assert z.val == space.EqSet([z,w])
        assert w.val == space.EqSet([z,w])

    def test_unify_circular(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x, y, z, w, a, b = (sp.var('x'), sp.var('y'),
                            sp.var('z'), sp.var('w'),
                            sp.var('a'), sp.var('b'))
        sp.bind(x, [y])
        sp.bind(y, [x])
        raises(space.UnificationFailure, sp.unify, x, y)
        sp.bind(z, [1, w])
        sp.bind(w, [z, 2])
        raises(space.UnificationFailure, sp.unify, z, w)
        sp.bind(a, {1:42, 2:b})
        sp.bind(b, {1:a,  2:42})
        raises(space.UnificationFailure, sp.unify, a, b)
        # check store consistency
        assert x.val == [y]
        assert y.val == [x]
        assert z.val == [1, w]
        assert w.val == [z, 2]
        assert a.val == {1:42, 2:b}
        assert b.val == {1:a,  2:42}
        
        
    def test_threads_creating_vars(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        def create_var(thread, *args):
            x = sp.var('x')

        def create_var2(thread, *args):
            raises(v.AlreadyExists, sp.var, 'x')

        t1, t2 = (FunThread(create_var),
                  FunThread(create_var2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()


    def test_threads_binding_vars(self):
        sp = space.ComputationSpace(problems.dummy_problem)

        def do_stuff(thread, var, val):
            thread.raised = False
            try:
                # pb. with TLS (thread-local-stuff) in
                # cs class
                sp.bind(var, val)
            except Exception, e:
                print e
                thread.raised = True
                assert isinstance(e, space.AlreadyBound)
            
        x = sp.var('x')
        vars_ = []
        for nvar in range(100):
            v = sp.var('x-'+str(nvar))
            sp.bind(x, v)
            vars_.append(v)
            
        for var in vars_:
            assert var in sp.vars
            assert var.val == x.val

        t1, t2 = (FunThread(do_stuff, x, 42),
                  FunThread(do_stuff, x, 43))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        #check that every var is really bound to 42 or 43
        for var in vars_:
            assert var in sp.vars
            assert var.val == x.val
        assert (t2.raised and not t1.raised) or \
               (t1.raised and not t2.raised)
    

    def test_threads_waiting_for_unbound_var(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        import time
        
        def near(v1, v2, err):
            return abs(v1 - v2) < err
        
        start_time = time.time()

        def wait_on_unbound(thread, var, start_time):
            thread.val = var.get()
            thread.waited = time.time() - start_time

        x = sp.var('x')
        t1, t2 = (FunThread(wait_on_unbound, x, start_time),
                  FunThread(wait_on_unbound, x, start_time))
        t1.start()
        t2.start()
        time.sleep(1)
        sp.bind(x, 42)
        t1.join()
        t2.join()
        assert t1.val == 42
        assert t2.val == 42
        assert near(t1.waited, 1, .1)
        assert near(t2.waited, 1, .1)


    def test_set_var_domain(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x = sp.var('x')
        sp.set_domain(x, [1, 3, 5])
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 3, 5])

    def test_bind_with_domain(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x = sp.var('x')
        sp.set_domain(x, [1, 2, 3])
        raises(space.OutOfDomain, sp.bind, x, 42)
        sp.bind(x, 3)
        assert x.val == 3

    def test_bind_with_incompatible_domains(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x, y = sp.var('x'), sp.var('y')
        sp.set_domain(x, [1, 2])
        sp.set_domain(y, [3, 4])
        raises(space.IncompatibleDomains, sp.bind, x, y)
        sp.set_domain(y, [2, 4])
        sp.bind(x, y)
        # check x and y are in the same equiv. set
        assert x.val == y.val


    def test_unify_with_domains(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.bind(x, [42, z])
        sp.bind(y, [z, 42])
        sp.set_domain(z, [1, 2, 3])
        raises(space.UnificationFailure, sp.unify, x, y)
        sp.set_domain(z, [41, 42, 43])
        sp.unify(x, y)
        assert z.val == 42
        assert z.cs_get_dom(sp) == c.FiniteDomain([41, 42, 43])

    def test_add_constraint(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        raises(c.DomainlessVariables,
               c.Expression, sp, [x, y, z], 'x == y + z')
        x.cs_set_dom(sp, c.FiniteDomain([1, 2]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        sp.add_constraint(k)
        assert k in sp.constraints

    def test_narrowing_domains_failure(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        x.cs_set_dom(sp, c.FiniteDomain([1, 2]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        raises(c.ConsistencyFailure, k.narrow)

    def test_narrowing_domains_success(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        x.cs_set_dom(sp, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        k.narrow()
        assert x.cs_get_dom(sp) == c.FiniteDomain([5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3])

    def test_compute_dependant_vars(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        x.cs_set_dom(sp, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        w.cs_set_dom(sp, c.FiniteDomain([1, 4, 5]))
        k1 = c.Expression(sp, [x, y, z], 'x == y + z')
        k2 = c.Expression(sp, [z, w], 'z < w')
        sp.add_constraint(k1)
        sp.add_constraint(k2)
        varset = set()
        constset = set()
        sp._compute_dependant_vars(k1, varset, constset)
        assert varset == set([x, y, z, w])
        assert constset == set([k1, k2])

    def test_store_satisfiable_success(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        x.cs_set_dom(sp, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        sp.add_constraint(k)
        assert sp.satisfiable(k) == True
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])
        
    def test_store_satisfiable_failure(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        x.cs_set_dom(sp, c.FiniteDomain([1, 2]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        sp.add_constraint(k)
        assert sp.satisfiable(k) == False
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])

    def test_satisfiable_many_const_success(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        x.cs_set_dom(sp, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        w.cs_set_dom(sp, c.FiniteDomain([1, 4, 5]))
        k1 = c.Expression(sp, [x, y, z], 'x == y + z')
        k2 = c.Expression(sp, [z, w], 'z < w')
        sp.add_constraint(k1)
        sp.add_constraint(k2)
        assert sp.satisfiable(k1) == True
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(sp) == c.FiniteDomain([1, 4, 5])
        assert sp.satisfiable(k2) == True
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(sp) == c.FiniteDomain([1, 4, 5])
        narrowed_doms = sp.get_satisfying_domains(k1)
        assert narrowed_doms == {x:c.FiniteDomain([5]),
                                 y:c.FiniteDomain([2]),
                                 z:c.FiniteDomain([3]),
                                 w:c.FiniteDomain([4, 5])}
        narrowed_doms = sp.get_satisfying_domains(k2)
        assert narrowed_doms == {x:c.FiniteDomain([5]),
                                 y:c.FiniteDomain([2]),
                                 z:c.FiniteDomain([3]),
                                 w:c.FiniteDomain([4, 5])}


    def test_satisfiable_many_const_failure(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        x.cs_set_dom(sp, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        w.cs_set_dom(sp, c.FiniteDomain([1]))
        k1 = c.Expression(sp, [x, y, z], 'x == y + z')
        k2 = c.Expression(sp, [z, w], 'z < w')
        sp.add_constraint(k1)
        sp.add_constraint(k2)
        assert sp.satisfiable(k1) == False
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(sp) == c.FiniteDomain([1])
        assert sp.satisfiable(k2) == False
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(sp) == c.FiniteDomain([1])
        narrowed_doms = sp.get_satisfying_domains(k1)
        assert narrowed_doms == {}
        narrowed_doms = sp.get_satisfying_domains(k2)
        assert narrowed_doms == {}

    def test_satisfy_many_const_failure(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        x.cs_set_dom(sp, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        w.cs_set_dom(sp, c.FiniteDomain([1]))
        k1 = c.Expression(sp, [x, y, z], 'x == y + z')
        k2 = c.Expression(sp, [z, w], 'z < w')
        sp.add_constraint(k1)
        sp.add_constraint(k2)
        raises(space.ConsistencyFailure, sp.satisfy, k1)
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(sp) == c.FiniteDomain([1])
        raises(space.ConsistencyFailure, sp.satisfy, k2)
        assert x.cs_get_dom(sp) == c.FiniteDomain([1, 2, 5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2, 3])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3, 4])
        assert w.cs_get_dom(sp) == c.FiniteDomain([1])
        
    def test_satisfy_many_const_success(self):
        sp = space.ComputationSpace(problems.dummy_problem)
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        x.cs_set_dom(sp, c.FiniteDomain([1, 2, 5]))
        y.cs_set_dom(sp, c.FiniteDomain([2, 3]))
        z.cs_set_dom(sp, c.FiniteDomain([3, 4]))
        w.cs_set_dom(sp, c.FiniteDomain([1, 4, 5]))
        k1 = c.Expression(sp, [x, y, z], 'x == y + z')
        k2 = c.Expression(sp, [z, w], 'z < w')
        sp.add_constraint(k1)
        sp.add_constraint(k2)
        sp.satisfy(k2)
        print x.cs_get_dom(sp)
        assert x.cs_get_dom(sp) == c.FiniteDomain([5])
        assert y.cs_get_dom(sp) == c.FiniteDomain([2])
        assert z.cs_get_dom(sp) == c.FiniteDomain([3])
        assert w.cs_get_dom(sp) == c.FiniteDomain([4, 5])


class TestComputationSpace:

    def setup_method(self, meth):
        pass

    def test_bind_cs_root(self):
        spc = space.ComputationSpace(problems.satisfiable_problem)
        assert '__root__' in spc.names
        assert set(['x', 'y', 'w']) == \
               set([var.name for var in spc.root.val])

    def test_ask_success(self):
        spc = space.ComputationSpace(problems.one_solution_problem)
        assert spc.ask() == space.Succeeded

    def test_double_ask(self):
        spc = space.ComputationSpace(problems.one_solution_problem)
        assert spc.ask() == space.Succeeded
        assert spc.ask() == space.Succeeded
        
    def test_ask_failure(self):
        spc = space.ComputationSpace(problems.unsatisfiable_problem)
        assert spc.ask() == space.Failed

    def test_ask_alternatives(self):
        spc = space.ComputationSpace(problems.satisfiable_problem)
        assert spc.ask() == space.Alternatives(2)

    def test_old_distribute(self):
        spc = space.ComputationSpace(problems.satisfiable_problem)
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

    def test_clone_and_distribute(self):
        spc = space.ComputationSpace(problems.satisfiable_problem)
        w = spc.get_var_by_name('w')
        assert spc.ask() == space.Alternatives(2)
        new_spc = spc.clone()
        # following couple of ops superceeded by inject()
        new_spc.add_constraint(c.Expression(new_spc, [w], 'w == 5'))
        new_spc._process()
        assert spc.ask() == space.Alternatives(2)
        assert new_spc.ask() == space.Succeeded
        assert w.cs_get_dom(spc) == c.FiniteDomain([5, 6, 7])
        assert w.cs_get_dom(new_spc) == c.FiniteDomain([5])

    def test_inject(self):
        def more_constraints(space):
            space.add_constraint(c.Expression(space, [w], 'w == 5'))
        spc = space.ComputationSpace(problems.satisfiable_problem)
        w = spc.get_var_by_name('w')
        assert spc.ask() == space.Alternatives(2)
        new_spc = spc.clone()
        new_spc.inject(more_constraints)
        assert spc.ask() == space.Alternatives(2)
        assert new_spc.ask() == space.Succeeded
        assert w.cs_get_dom(spc) == c.FiniteDomain([5, 6, 7])
        assert w.cs_get_dom(new_spc) == c.FiniteDomain([5])
        
    def test_merge(self):
        spc = space.ComputationSpace(problems.satisfiable_problem)
        x, y, z, w = spc.find_vars('x', 'y', 'z', 'w')
        assert spc.TOP
        assert spc.ask() == space.Alternatives(2)
        assert spc.dom(x) == c.FiniteDomain([6])
        assert spc.dom(y) == c.FiniteDomain([2])
        assert spc.dom(z) == c.FiniteDomain([4])
        assert spc.dom(w) == c.FiniteDomain([5, 6, 7])

        def more_constraints(space):
            space.add_constraint(c.Expression(space, [w], 'w == 5'))

        nspc = spc.clone()
        nspc.inject(more_constraints)
        x, y, z, w = nspc.find_vars('x', 'y', 'z', 'w')
        assert not nspc.TOP
        assert nspc.dom(x) == c.FiniteDomain([6])
        assert nspc.dom(y) == c.FiniteDomain([2])
        assert nspc.dom(z) == c.FiniteDomain([4])
        assert nspc.dom(w) == c.FiniteDomain([5])
        assert nspc.ask() == space.Succeeded
        nspc.merge()
        assert nspc.ask() == space.Merged
        assert x.val == 6
        assert y.val == 2
        assert w.val == 5
        assert (x, w, y) == nspc.root.val
