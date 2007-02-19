import os

from pypy.rlib import rconstraint as rc, rdomain as rd
from pypy.rlib import rpropagation as rp, rdistributor as rdist


def debug(msg): 
    os.write(2, "debug: " + msg + '\n')

N = 32

def _disp_sols(sols):
    for s in sols:
        os.write(1, "solution\n")
        for var, val in s.items():
            os.write(1, '  %s = %d\n' % (var, val))
    

def test_binlt():
    "binary exprs and alldistinctness test"
    dom = {}
    for i in range(N):
        dom[i] = True
    D1 = rd.BaseFiniteDomain( dom )
    D2 = rd.BaseFiniteDomain( dom )
    vars = ["a", "b"]
    constraints = []
    constr = rc.BinLt( vars )
    constr.revise( {"a":D1,"b":D2} )
    constraints.append( constr )
    rep = rp.Repository({"a":D1,"b":D2}, constraints)
    sols = rep.solve_all(rdist.DichotomyDistributor())

    assert len(sols) == N * (N - 1) / 2
    
    for s in sols:
        a = s['a']
        b = s['b']
        assert a < b

    return 0


def test_alldistinct():
    dom = {}
    for i in range(N):
        dom[i] = True
    D1 = rd.BaseFiniteDomain( dom )
    D2 = rd.BaseFiniteDomain( dom )
    vars = ["a", "b"]
    constraints = []
    constr = rc.AllDistinct( vars )
    constr.revise( {"a":D1,"b":D2} )
    constraints.append(constr)
    rep = rp.Repository({"a":D1,"b":D2}, constraints)
    sols = rep.solve_all(rdist.DichotomyDistributor())

    assert len(sols) == N * (N - 1)
    for s in sols:
        a = s['a']
        b = s['b']
        assert a != b

    return 0


class FooConstraint(rc.Expression):

    def filter_func(self, kwargs):
        a, b, c = kwargs.values()
        return a == b + c

def test_nary_expr():
    dom = {}
    for i in range(N):
        dom[i] = True
    D1 = rd.BaseFiniteDomain( dom )
    D2 = rd.BaseFiniteDomain( dom )
    D3 = rd.BaseFiniteDomain( dom )
    vars = ["a", "b", "c"]
    constraints = []
    constr = FooConstraint( vars )
    constr.revise( {"a":D1,"b":D2, "c":D3} )
    constraints.append(constr)
    rep = rp.Repository({"a":D1,"b":D2, "c":D3}, constraints)
    sols = rep.solve_all(rdist.DichotomyDistributor())

    assert len(sols) == N * (N + 1) / 2
    for s in sols:
        a = s['a']
        b = s['b']
        c = s['c']
        assert a == b + c

    return 0
