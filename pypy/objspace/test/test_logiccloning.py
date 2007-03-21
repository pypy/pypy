try:
    from pypy.conftest import gettestobjspace, option
    from py.test import skip
except ImportError:
    pass

class AppTest_CompSpaceCloning(object):

    def setup_class(cls):
        if not option.runappdirect:
            skip('pure pypy-logic test (try with _test_logic_build)')
        cls.space = gettestobjspace('logic')
        
    
    def test_full_logic_program(self):
        # this used to work at some point
        from constraint.solver import solve
        from cclp import newspace, choose, switch_debug_info
        
        def soft():
            choice = choose(2)
            if choice == 1:
                return 'beige'
            else:
                return 'coral'

        def hard():
            choice = choose(2)
            if choice == 1:
                return 'mauve'
            else:
                return 'ochre'

        def contrast(C1, C2):
            choice = choose(2)
            if choice == 1:
                unify(C1, soft())
                unify(C2, hard())
            else:
                unify(C1, hard())
                unify(C2, soft())

        def suit():
            Shirt, Pants, Socks = newvar(), newvar(), newvar()
            contrast(Shirt, Pants)
            contrast(Pants, Socks)
            if Shirt == Socks: fail()
            return (Shirt, Pants, Socks)

        s = newspace(suit)
        from pprint import pprint
        sols = set()
        for sol in solve(s):
            sols.add(sol)

        pprint(list(sols))
        assert sols == set([('beige', 'mauve', 'coral'),
                            ('beige', 'ochre', 'coral'),
                            ('coral', 'mauve', 'beige'),
                            ('coral', 'ochre', 'beige'),
                            ('mauve', 'beige', 'ochre'),
                            ('mauve', 'coral', 'ochre'),
                            ('ochre', 'beige', 'mauve'),
                            ('ochre', 'coral', 'mauve')])

            

    def test_relational_append(self):
        skip('next, ensure this works')
        from cclp import newspace, choose
        from constraint.solver import solve

        def append(A, B, C):
            choice = choose(2)
            try:
                if choice == 1:
                    unify(A, None)
                    unify(B, C)
                    return A, B
                else:
                    Atail, Ctail, X = newvar(), newvar(), newvar()
                    unify(A, (X, Atail))
                    unify(C, (X, Ctail))
                    return append(Atail, B, Ctail)
                return A, B
            except:
                import traceback
                traceback.print_exc()

        def in_space():
            X, Y = newvar(), newvar()
            return append(X, Y, (1, (2, (3, None))))
        
        s = newspace(in_space)

        for sol in solve(s):
            print "SOL", sol
##             assert sol in ((None, (1,(2,(3,None)))),
##                            ((1,None), (2,(3,None))),
##                            ((1,(2,None)), (3,None)),
##                            ((1,(2,(3,None))), None))


    def test_cloning_queens(self):
        skip('next, ensure this works')
        from constraint.solver import solve
        from constraint.examples import queens1, queens2
        from cclp import newspace

        for queen in (queens1, queens2):
            sols = set()
            s = newspace(queen, 8)
            for sol in solve(s):
                sols.add(sol)
                print sol
            #assert len(sols) == 2


    def test_recomputing_solver(self):
        skip('next, ensure this works')
        from constraint.examples import conference_scheduling
        from constraint import solver
        from cclp import newspace, switch_debug_info

        switch_debug_info()
        s = newspace(conference_scheduling)

        sols = set()
        for sol in solver.solve_recomputing(s):
            sols.add(tuple(sol))
            print sol
        assert len(sols) == 64
