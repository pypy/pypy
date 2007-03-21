from pypy.rlib.cslib.rpropagation import Repository, Solver
import pypy.rlib.cslib.rdistributor as rd

from pypy.module._cslib import fd
from pypy.module._cslib.constraint import W_AbstractConstraint

from pypy.interpreter.error import OperationError

from pypy.interpreter import typedef, gateway, baseobjspace
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.dictobject import W_DictObject


class _Repository(Repository):

    def __init__(self, space, w_variables, w_domains, w_constraints):
        # let's just give everything unwrapped to our parent
        doms = {}
        for var, dom in w_domains.content.items():
            assert isinstance( dom, fd.W_FiniteDomain )
            assert isinstance( var, W_StringObject )
            doms[space.str_w(var)] = dom.domain
        constraints = []
        for w_constraint in space.unpackiterable( w_constraints ):
            if not isinstance( w_constraint, W_AbstractConstraint ):
                raise OperationError( space.w_TypeError,
                                      space.wrap("constraints needs to be a sequence of constraints" ) )
            constraints.append( w_constraint.constraint )
        Repository.__init__(self, doms, constraints)


class W_Repository(baseobjspace.Wrappable):

    def __init__(self, space, w_variables, w_domains, w_constraints):
        self.repo = _Repository(space, w_variables, w_domains, w_constraints)


W_Repository.typedef = typedef.TypeDef("W_Repository")

def make_repo(space, w_variables, w_domains, w_constraints):
    if not isinstance(w_domains,W_DictObject):
        raise OperationError(space.w_TypeError,
                               space.wrap('domains must be a dictionary'))
    return W_Repository(space, w_variables, w_domains, w_constraints)

                            
class W_Solver(baseobjspace.Wrappable):

    def __init__(self, space):
        self.space = space
        self.solver = Solver(rd.DefaultDistributor())

    def w_solve(self, w_repo, w_verbosity):
        space = self.space
        if not isinstance(w_repo, W_Repository):
            raise OperationError(space.w_TypeError,
                                 space.wrap('first argument must be a repository.'))
        if not isinstance(w_verbosity, W_IntObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap('second argument must be an int.'))
        self._verb = w_verbosity.intval
        sols = self.solver.solve_all(w_repo.repo)
        sols_w = []
        for sol in sols:
            w_dict = space.newdict()
            for var,value in sol.items():
                domain = w_repo.repo._domains[var]
                assert isinstance( domain, fd._FiniteDomain )
                w_var = space.wrap(var)
                w_value = domain.vlist[value]
                space.setitem( w_dict, w_var, w_value )
            sols_w.append( w_dict )
        return space.newlist(sols_w)

W_Solver.typedef = typedef.TypeDef(
    'W_Solver',
    solve = interp2app(W_Solver.w_solve))
                                   

def make_solver(space):
    return W_Solver(space)
