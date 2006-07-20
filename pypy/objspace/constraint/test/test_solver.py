from pypy.conftest import gettestobjspace
from py.test import skip

class AppTest_Solver(object):
    skip("currently unplugged")
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic', usemodules=('_stackless', ))

    def test_instantiate(self):
        import solver, problems
        spc = newspace()

        spc.define_problem(problems.conference_scheduling)
        
        sols = solver.solve(spc)
        assert str(type(sols)) == "<type 'generator'>"

    def test_solve(self):
        import solver, problems
        spc = newspace()

        spc.define_problem(problems.conference_scheduling)
        
        sols = solver.solve(spc)
        solutions = set()
        for sol in sols:
            solutions.add(sol)
        assert len(solutions) == 64
