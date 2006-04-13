from pypy.conftest import gettestobjspace

class AppTest_Solver(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_instantiate(self):
        from pypy.objspace.constraint.applevel import solver, problems
        spc = newspace()

        spc.define_problem(problems.conference_scheduling)
        
        sols = solver.solve(spc)
        assert str(type(sols)) == "<type 'generator'>"

    def test_solve(self):
        from pypy.objspace.constraint.applevel import solver, problems
        spc = newspace()

        spc.define_problem(problems.conference_scheduling)
        
        sols = solver.solve(spc)
        count = 0
        solutions = set()
        for sol in sols:
            assert sol not in solutions
            solutions.add(sol)
            count += 1
        assert count == 64
