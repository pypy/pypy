from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.stringobject import W_StringObject

from pypy.objspace.constraint.domain import W_AbstractDomain


all_mms = {}

#-- Variables ---------------------------

class W_Variable(Wrappable):
    def __init__(self, obj_space, w_name):
        self._space = obj_space
        self.w_name = w_name

    def name_w(self):
        return self._space.str_w(self.w_name)
    
    def w_name(self):
        return self.w_name

W_Variable.typedef = typedef.TypeDef(
    "W_Variable",
    name = interp2app(W_Variable.w_name))

#-- Constraints -------------------------

class W_Constraint(Wrappable):
    def __init__(self, object_space):
        self._space = object_space

    def w_affected_variables(self):
        pass

    def w_is_variable_relevant(self, w_var):
        pass

    def w_estimate_cost(self, w_cs):
        pass

    def w_revise(self, w_cs):
        pass
    
W_Constraint.typedef = typedef.TypeDef(
    "W_Constraint",
    affected_variables = interp2app(W_Constraint.w_affected_variables),
    is_variable_relevant = interp2app(W_Constraint.w_is_variable_relevant),
    estimate_cost = interp2app(W_Constraint.w_estimate_cost),
    revise = interp2app(W_Constraint.w_revise))


#-- Distributors (standards) ------------

class W_Distributor(Wrappable):

    def __init__(self, object_space, fanout_w):
        self._space = object_space
        self.fanout = fanout_w

W_Distributor.typedef = typedef.TypeDef("W_Distributor")


#-- Computation space -------------------
from pypy.objspace.constraint.distributor import make_dichotomy_distributor


class W_ComputationSpace(Wrappable):
    def __init__(self, obj_space):
        self._space = obj_space
        self.distributor = make_dichotomy_distributor(self._space)
        # var -> dom, name->var
        self.var_dom = {}
        self.name_var = {}
        # constraint set
        self.constraints = {}
        # var -> constraints
        self.var_const = {}
        # freshly added constraints (tell -> propagate)
        self.to_check = {}
        self.status = None
        self.sol_set = obj_space.newlist([])

    #-- public interface ---------------
    
    def w_ask(self):
        if self.status is not None: return self.status
        try:
            if len(self.to_check) > 0:
                self.propagate()
        except: # FIXME: ConcistencyFailure
            self.status = self._space.newint(0)
            return self.status
        try:
            self.distributor.find_distribution_variable(self)
        except: # FIXME: indexError ?
            self.status = self._space.newint(1)
            return self.status
        self.status = self._space.newint(self.distributor.fanout)
        return self.status

    def w_clone(self):
        new = newspace(self._space)
        new.distributor = self.distributor
        # copy the domains only
        for var, dom in self.var_dom.items():
            new.var_dom[var] = dom.w_copy()
        # keep track of constraint check-list
        for const in self.to_check:
            new.to_check[const] = True
        # share other stateless stuff
        # this sharing will pose problems ...
        new.constraints = self.constraints
        new.var_const = self.var_const
        new.name_var = self.name_var
        new.sol_set = self.sol_set
        return new

    def w_commit(self, w_choice):
        self.distributor.w_distribute(self, w_choice)
        self.status = None

    def w_set_distributor(self, w_distributor):
        self.distributor = w_distributor

    def w_var(self, w_name, w_domain):
        assert isinstance(w_name, W_StringObject)
        assert isinstance(w_domain, W_AbstractDomain)
        name = self._space.str_w(w_name)
        if name in self.name_var:
            raise OperationError(self._space.w_RuntimeError,
                                 self._space.wrap("Name already used"))
        var = W_Variable(self._space, w_name)
        self.var_dom[var] = w_domain
        self.name_var[name] = var
        return var

    def w_find_var(self, w_name):
        return self.name_var[self._space.str_w(w_name)]

    def w_find_vars(self, w_vars):
        res = []
        for var in w_vars.wrappeditems:
            res.append(self.w_find_var(var))
        return self._space.newlist(res)

    def w_dom(self, w_variable):
        assert isinstance(w_variable, W_Variable)
        return self.var_dom[w_variable]

    def w_tell(self, w_constraint):
        assert isinstance(w_constraint, W_Constraint)
        self.constraints[w_constraint] = self._space.w_True
        for var in w_constraint.affected_variables():
            self.var_const.setdefault(var, [])
            self.var_const[var].append(w_constraint)
        self.to_check[w_constraint] = True

    def w_dependant_constraints(self, w_var):
        return self._space.newlist(self.dependant_constraints(w_var))

    def w_define_problem(self, w_problem):
        self.sol_set = self._space.call(w_problem, self._space.newlist([self]))

    def w_merge(self):
        res = []
        for var in self.sol_set.wrappeditems:
            res.append(self.var_dom[var].get_values()[0])
        return self._space.newtuple(res)

    def w_test_solution(self, w_sol):
        varset = {}
        for var, val in zip(self.sol_set.wrappeditems,
                            w_sol.wrappeditems):
            varset[var.w_name] = val
        for _const in self.constraints:
            if not _const.test_solution(varset):
                print "Solution", sol, "doesn't satisfy", _const
                return self._space.newbool(False)
        return self._space.newbool(True)


    def w_print_state(self):
        print "VARS  :", self.name_var.keys()
        print "CONST :", self.var_const.values()
        print "DOMS  :", self.var_dom.values()
        print "CHK   :", self.to_check

    #-- everything else ---------------

    def dependant_constraints(self, var):
        try:
            return self.var_const[var]
        except KeyError:
            return []

    def propagate(self):
        const_q = [(const.estimate_cost_w(self), const)
                   for const in self.to_check]
        self.to_check = {}
        assert const_q != []
        const_q.sort()
        const_q.reverse() # for pop() friendlyness
        affected_constraints = {}
        while True:
            if not const_q:
                const_q = [(const.estimate_cost_w(self), const)
                           for const in affected_constraints]
                if not const_q:
                    break
                const_q.sort()
                affected_constraints.clear()
            cost, const = const_q.pop()
            entailed = const.revise(self)
            for var in const.affected_variables():
                dom = self.w_dom(var)
                if not dom.has_changed():
                    continue
                for dependant_const in self.dependant_constraints(var):
                    if dependant_const is not const:
                        affected_constraints[dependant_const] = True
                dom.w_reset_flags()
            if entailed:
                # we should also remove the constraint from
                # the set of satifiable constraints of the space
                if const in affected_constraints:
                    del affected_constraints[const]
        

W_ComputationSpace.typedef = typedef.TypeDef(
    "W_ComputationSpace",
    var = interp2app(W_ComputationSpace.w_var),
    find_var = interp2app(W_ComputationSpace.w_find_var),
    find_vars = interp2app(W_ComputationSpace.w_find_vars),
    dom = interp2app(W_ComputationSpace.w_dom),
    tell = interp2app(W_ComputationSpace.w_tell),
    ask = interp2app(W_ComputationSpace.w_ask),
    clone = interp2app(W_ComputationSpace.w_clone),
    commit = interp2app(W_ComputationSpace.w_commit),
    merge = interp2app(W_ComputationSpace.w_merge),
    dependant_constraints = interp2app(W_ComputationSpace.w_dependant_constraints),
    define_problem = interp2app(W_ComputationSpace.w_define_problem),
    test_solution = interp2app(W_ComputationSpace.w_test_solution),
    print_state = interp2app(W_ComputationSpace.w_print_state))

def newspace(object_space):
    return W_ComputationSpace(object_space)
app_newspace = gateway.interp2app(newspace)
