from pypy.conftest import gettestobjspace

class AppTest_Solver(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

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
