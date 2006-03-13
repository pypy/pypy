from threading import Thread

import variable as v
import constraint as c
import computationspace as space
import distributor as di
import problems
try:
    from py.test import raises
except ImportError:
    def raises(*args):
        pass

#-- utility ---------------------

class FunThread(Thread):

    def __init__(self, fun, *args):
        Thread.__init__(self)
        self.fun = fun
        self.args = args

    def run(self):
        self.fun(self, *self.args)

def newspace(problem=problems.dummy_problem):
    return space.ComputationSpace(problem)

#-- meat ------------------------

class TestStoreUnification:
    

    def test_already_in_store(self):
        sp = newspace()
        x = sp.var('x')
        raises(v.AlreadyInStore, sp.var, 'x')

    def test_already_bound(self):
        sp = newspace()
        x = sp.var('x')
        sp.bind(x, 42)
        sp.bind(x, 42)
        raises(space.UnificationFailure, sp.bind, x, 43)

    def test_bind_var_var(self):
        sp = newspace()
        x, y, z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.bind(x, z)
        assert x.val == space.EqSet([x, z])
        assert y.val == space.EqSet([y])
        assert z.val == space.EqSet([x, z])
        z.bind(42)
        assert z.val == 42
        assert x.val == 42
        y.bind(42)
        assert y.val == 42
        y.bind(z)

    def test_bind_var_val(self):
        sp = newspace()
        x, y, z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.bind(x, z)
        sp.bind(y, 42)
        sp.bind(z, 3.14)
        assert x.val == 3.14
        assert y.val == 42
        assert z.val == 3.14

    def test_unify_same(self):
        sp = newspace()
        x,y,z,w = (sp.var('x'), sp.var('y'),
                   sp.var('z'), sp.var('w'))
        sp.bind(x, [42, z])
        sp.bind(y, [z, 42])
        sp.bind(w, [z, 43])
        raises(space.UnificationFailure, sp.unify, x, w)
        sp.unify(x, y)
        assert z.val == 42

    def test_double_unification(self):
        sp = newspace()
        x, y, z = (sp.var('x'), sp.var('y'),
                   sp.var('z'))
        sp.bind(x, 42)
        sp.bind(y, z)
        sp.unify(x, y)
        assert z.val == 42
        sp.unify(x, y)
        assert (z.val == x.val) and (x.val == y.val)


    def test_unify_values(self):
        sp = newspace()
        x, y = sp.var('x'), sp.var('y')
        sp.bind(x, [1, 2, 3])
        sp.bind(y, [1, 2, 3])
        sp.unify(x, y)
        assert x.val == [1, 2, 3]
        assert y.val == [1, 2, 3]

    def test_unify_lists_success(self):
        sp = newspace()
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
        sp = newspace()
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
        sp = newspace()
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.bind(x, [42, z])
        sp.bind(y, [z, 44])
        raises(space.UnificationFailure, sp.unify, x, y)
        # check store consistency
        assert x.val == [42, z]
        assert y.val == [z, 44]
        assert z.val == space.EqSet([z])

    def test_unify_failure2(self):
        sp = newspace()
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
        sp = newspace()
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
        sp = newspace()
        def create_var(thread, *args):
            x = sp.var('x')

        def create_var2(thread, *args):
            raises(v.AlreadyInStore, sp.var, 'x')

        t1, t2 = (FunThread(create_var),
                  FunThread(create_var2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()


    def test_threads_binding_vars(self):
        sp = newspace()

        def do_stuff(thread, var, val):
            thread.raised = False
            try:
                # pb. with TLS (thread-local-stuff) in
                # cs class
                sp.bind(var, val)
            except Exception, e:
                print e
                thread.raised = True
                assert isinstance(e, space.UnificationFailure)
            
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
        sp = newspace()
        import time
        
        def near(v1, v2, err):
            return abs(v1 - v2) < err
        
        start_time = time.time()

        def wait_on_unbound(thread, var, start_time):
            thread.val = var.wait()
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
        sp = newspace()
        x = sp.var('x')
        sp.set_dom(x, [1, 3, 5])
        assert sp.dom(x) == c.FiniteDomain([1, 3, 5])

    def test_bind_with_domain(self):
        sp = newspace()
        x = sp.var('x')
        sp.set_dom(x, [1, 2, 3])
        raises(space.OutOfDomain, sp.bind, x, 42)
        sp.bind(x, 3)
        assert x.val == 3

    def test_bind_with_incompatible_domains(self):
        sp = newspace()
        x, y = sp.var('x'), sp.var('y')
        sp.set_dom(x, [1, 2])
        sp.set_dom(y, [3, 4])
        raises(space.IncompatibleDomains, sp.bind, x, y)
        sp.set_dom(y, [2, 4])
        sp.bind(x, y)
        # check x and y are in the same equiv. set
        assert x.val == y.val


    def test_unify_with_domains(self):
        sp = newspace()
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.bind(x, [42, z])
        sp.bind(y, [z, 42])
        sp.set_dom(z, [1, 2, 3])
        raises(space.UnificationFailure, sp.unify, x, y)
        sp.set_dom(z, [41, 42, 43])
        sp.unify(x, y)
        assert z.val == 42
        assert sp.dom(z) == c.FiniteDomain([41, 42, 43])

    def test_add_expression(self):
        sp = newspace()
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        raises(c.DomainlessVariables,
               c.Expression, sp, [x, y, z], 'x == y + z')
        sp.set_dom(x, c.FiniteDomain([1, 2]))
        sp.set_dom(y, c.FiniteDomain([2, 3]))
        sp.set_dom(z, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        sp.add_expression(k)
        assert k in sp.constraints

    def test_narrowing_domains_failure(self):
        sp = newspace()
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.set_dom(x, c.FiniteDomain([1, 2]))
        sp.set_dom(y, c.FiniteDomain([2, 3]))
        sp.set_dom(z, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        raises(c.ConsistencyFailure, k.revise3)

    def test_narrowing_domains_success(self):
        sp = newspace()
        x,y,z = sp.var('x'), sp.var('y'), sp.var('z')
        sp.set_dom(x, c.FiniteDomain([1, 2, 5]))
        sp.set_dom(y, c.FiniteDomain([2, 3]))
        sp.set_dom(z, c.FiniteDomain([3, 4]))
        k = c.Expression(sp, [x, y, z], 'x == y + z')
        k.revise3()
        assert sp.dom(x) == c.FiniteDomain([5])
        assert sp.dom(y) == c.FiniteDomain([2])
        assert sp.dom(z) == c.FiniteDomain([3])

#-- computation spaces -------------------------------

import strategies

class TestComputationSpace:

    def setup_method(self, meth):
        pass

    def test_bind_cs_root(self):
        spc = newspace(problems.satisfiable_problem)
        assert '__root__' in spc.names
        assert set(['x', 'y', 'z']) == \
               set([var.name for var in spc.root.val])
        
    def test_ask_alternatives(self):
        spc = newspace(problems.satisfiable_problem)
        assert spc.ask() == space.Alternative(2)

    def test_clone(self):
        """checks that a chain of initially s1 = s2
           s1 - commit(1) - commit(1) ...
           s2 - clone - commit(1) - clone - commit(1) ...
           converges toward the same solution
        """
        s1 = newspace(problems.conference_scheduling)
        s2 = s1

        def eager_and(t1,  t2):
            return t1 and t2

        while not (eager_and(s2.ask() == space.Succeeded,
                             s1.ask() == space.Succeeded)):
            #print "S1", s1.pretty_doms()
            #print "S2", s2.pretty_doms()
            #assert s1 == s2
            temp = s2.clone()
            temp.ask()
            s2 = temp
            s1.commit(1)
            s2.commit(1)

    def test_inject(self):
        def more_constraints(space):
            x, y, z = new_spc.find_vars('x', 'y', 'z')
            space.add_constraint([x], 'x == 0')
            space.add_constraint([z, y], 'z == y')
            space.add_constraint([y], 'y < 2')

        spc = newspace(problems.satisfiable_problem)
        assert spc.ask() == space.Alternative(2)
        new_spc = spc.clone()
        new_spc.ask()
        new_spc.inject(more_constraints)
        assert spc.ask() == space.Alternative(2)
        assert new_spc.ask() == space.Succeeded
        
    def test_merge(self):
        def more_constraints(space):
            x, y, z = new_spc.find_vars('x', 'y', 'z')
            space.add_constraint([x], 'x == 0')
            space.add_constraint([z, y], 'z == y')
            space.add_constraint([y], 'y < 2')

        spc = newspace(problems.satisfiable_problem)
        assert spc.ask() == space.Alternative(2)
        new_spc = spc.clone()
        new_spc.ask()
        new_spc.inject(more_constraints)
        assert spc.ask() == space.Alternative(2)
        assert new_spc.ask() == space.Succeeded
        x, y, z = new_spc.find_vars('x', 'y', 'z')
        res = new_spc.merge()
        assert res.values() == [0, 0, 0]
        
    def test_scheduling_dfs_one_solution(self):
        sol = strategies.dfs_one(problems.conference_scheduling)

        spc = space.ComputationSpace(problems.conference_scheduling)
        assert spc.test_solution( sol )
        

    def test_scheduling_all_solutions_dfs(self):
        sols = strategies.solve_all(problems.conference_scheduling)
        assert len(sols) == 64
        spc = space.ComputationSpace(problems.conference_scheduling)
        for s in sols:
            assert spc.test_solution( s )
            

    def test_scheduling_all_solutions_lazily_dfs(self):
        sp = space.ComputationSpace(problems.conference_scheduling)
        for sol in strategies.lazily_solve_all(sp):
            assert sp.test_solution(sol)

    def test_scheduling_all_solutions_bfs(self):
        sols = strategies.solve_all(problems.conference_scheduling,
                                    direction=strategies.Breadth)
        assert len(sols) == 64
        spc = space.ComputationSpace(problems.conference_scheduling)
        for s in sols:
            assert spc.test_solution( s )
            

    def test_scheduling_all_solutions_lazily_bfs(self):
        sp = space.ComputationSpace(problems.conference_scheduling)
        for sol in strategies.lazily_solve_all(sp, direction=strategies.Breadth):
            assert sp.test_solution(sol)


    def no_test_sudoku(self):
        #spc = newspace(problems.sudoku)
        #print spc.constraints
        def more_constraints(space):
            f = 'puzzle1.su'
            
            file = open(f)
            c = []
            row = 1
            for line in file.readlines():
                for col in range(1,10):
                    if line[col-1] != ' ':
                        tup = ('v%d%d' % (col, row), int(line[col-1]))
                        space.add_constraint([space.get_var_by_name(tup[0])],'%s == %d' % tup)
                row += 1
                
        #nspc = spc.clone()
        #nspc.inject(more_constraints)
        #print nspc.constraints
        sol2 = strategies.dfs_one(strategies.sudoku)
        print "done dfs"
        #sol2 = [var.val for var in sol]
