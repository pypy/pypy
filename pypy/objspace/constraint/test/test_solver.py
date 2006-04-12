from pypy.conftest import gettestobjspace

class AppTest_Solver(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_instantiate(self):
        from pypy.objspace.constraint.applevel import solver, problems
        spc = newspace()

        spc.set_root(problems.conference_scheduling(spc))
        #FIXME: that 'interation over non-sequence' kills me ...
        #spc.define_problem(problems.conference_scheduling)
        
        sols = solver.solve(spc)
        assert str(type(sols)) == "<type 'generator'>"
