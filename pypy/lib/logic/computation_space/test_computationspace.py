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
    
    def test_get_by_name(self):
        sp = newspace()
        x = sp.var('x')
        assert x == sp.get_var_by_name('x')
        raises(space.NotInStore, sp.get_var_by_name, 'y')

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

import solvers

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
        sol = solvers.dfs_one(problems.conference_scheduling)

        spc = space.ComputationSpace(problems.conference_scheduling)
        assert spc.test_solution( sol )
        

    def test_scheduling_all_solutions_dfs(self):
        sols = solvers.solve_all(problems.conference_scheduling)
        assert len(sols) == 64
        spc = space.ComputationSpace(problems.conference_scheduling)
        for s in sols:
            assert spc.test_solution( s )
            

    def test_scheduling_all_solutions_lazily_dfs(self):
        sp = space.ComputationSpace(problems.conference_scheduling)
        for sol in solvers.lazily_solve_all(sp):
            assert sp.test_solution(sol)

    def test_scheduling_all_solutions_bfs(self):
        sols = solvers.solve_all(problems.conference_scheduling,
                                    direction=solvers.Breadth)
        assert len(sols) == 64
        spc = space.ComputationSpace(problems.conference_scheduling)
        for s in sols:
            assert spc.test_solution( s )
            

    def test_scheduling_all_solutions_lazily_bfs(self):
        sp = space.ComputationSpace(problems.conference_scheduling)
        for sol in solvers.lazily_solve_all(sp, direction=solvers.Breadth):
            assert sp.test_solution(sol)


    def notest_sudoku(self):
        spc = newspace(problems.sudoku)
        print spc.constraints

        def more_constraints(space):
            fname = 'puzzle1.su'
            
            f = open(fname)
            c = []
            row = 1
            for line in f.readlines():
                for col in range(1,10):
                    if line[col-1] != ' ':
                        tup = ('v%d%d' % (col, row), int(line[col-1]))
                        space.add_constraint([space.get_var_by_name(tup[0])],'%s == %d' % tup)
                row += 1
                
        spc.inject(more_constraints)
        print spc.constraints
        sol_iter = solvers.lazily_solve_all(spc)
        sol = sol_iter.next()    
        print sol
        assert spc.test_solution(sol)
