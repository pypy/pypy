# TODO
# * [1] adapt other distribution strategies
# * [5] add a linear constraint solver (vital for fast
#   constraint propagation over finite integer domains)
#   and other kinds of specialized propagators

from variable import Var, NoValue, NoDom
from constraint import FiniteDomain, ConsistencyFailure, \
     Expression
from distributor import DefaultDistributor
import event # NewSpace, Clone, Revise

Failed = 0
Succeeded = 1

def NoProblem():
    """the empty problem, used by clone()"""
    pass
        
#----------- Store Exceptions ----------------------------

class NotInStore(Exception):
    def __init__(self, name):
        self.name = name
    
    def __str__(self):
        return "%s not in the store" % self.name

class UnificationFailure(Exception):
    def __init__(self, var1, var2, cause=None):
        self.var1, self.var2 = (var1, var2)
        self.cause = cause
    def __str__(self):
        diag = "%s %s can't be unified" % \
               (self.var1, self.var2)
        if self.cause:
            diag += " because %s" % self.cause
        return diag
    
#---- ComputationSpace -------------------------------
class ComputationSpace(object):

    # convenience id
    _id_count = 0

    def __init__(self, problem, parent=None):
        self.id = ComputationSpace._id_count
        ComputationSpace._id_count += 1
        self.status = None
        # consistency-preserving stuff
        self.in_transaction = False
        self.distributor = DefaultDistributor(self)
        # mapping from domains to variables
        self.doms = {}
        # set of all constraints 
        self.constraints = set()
        # mapping from vars to constraints
        self.var_const_map = {}
        self.event_set = set()
        
        if parent is None:
            self.vars = set()
            # mapping of names to vars (all of them)
            self.names = {}
            self.root = self.var('__root__')
            # set up the problem
            self.bind(self.root, problem(self))
        else:
            # shared stuff
            self.vars = parent.vars
            self.names = parent.names
            self.root = parent.root
            # copied stuff
            self.copy_domains(parent)
            self.copy_constraints(parent)
            # ...
            self.status = None
            self.distributor = parent.distributor.__class__(self)

#-- utilities & instrumentation -----------------------------

    def __str__(self):
        ret = ["<space:\n"]
        for v, d in self.doms.items():
            if self.dom(v) != NoDom:
                ret.append('  ('+str(v)+':'+str(d)+')\n')
        ret.append(">")
        return ' '.join(ret)

    def __repr__(self):
        return "<space n°%s>" % self.id

    def __eq__(self, spc):
        """space equality defined as :
           * identity, or
           * same set of vars with a domain, and
           * same name set, and
           * equal domains, and
           * same set of constraints, and
           * different propagators of the same type"""
        if not isinstance(spc, ComputationSpace): return False
        if id(self) == id(spc): return True
        r1 = self.vars == spc.vars
        r2 = self.names == spc.names
        r3 = self.constraints != spc.constraints
        r4 = self.distributor != spc.distributor
        r5 = self.root == spc.root
        if not r1 and r2 and r3 and r4 and r5:
            return False
        # now the domains
        it1 = [item for item in self.doms.items()
               if item[1] != NoDom]
        it2 = [item for item in spc.doms.items()
               if item[1] != NoDom]
        it1.sort()
        it2.sort()
        for (v1, d1), (v2, d2) in zip (it1, it2):
            if v1 != v2: return False
            if d1 != d2: return False
            if id(v1) != id(v2): return False
            if id(d1) == id(d2): return False
        return True

    def __ne__(self, other):
        return not self == other

    def pretty_doms(self):
        print "(-- domains --"
        doms = self.doms.items()
        doms.sort()
        for v, d in doms:
            if d != NoDom:
                print ' ', str(d.get_values())
        print " -- domains --)"

    def test_solution(self, sol):
        res = True
        for _const in self.constraints:
            if not _const.test_solution(sol):
                print "Solution", sol, "doesn't satisfy", _const
                res = False
        return res

#-- Computation Space -----------------------------------------

    #-- space helpers -----------------------------------------

    def _propagate(self):
        """wraps the propagator"""
        if len(self.event_set):
            try:
                self.satisfy_all()
            except ConsistencyFailure:
                self.status = Failed
            else:
                if not self._distributable():
                    self.status = Succeeded

    def _distributable(self):
        if self.status not in (Failed, Succeeded):
            for var in self.root.val:
                if self.dom(var).size() > 1 :
                    return True
        return False

    def _notify(self, event):
        self.event_set.add(event)

    #-- space official API ------------------------------------

    def ask(self):
        self._propagate()
        if self.status in (Failed, Succeeded):
            return self.status
        if self._distributable():
            return self.distributor.nb_subdomains()

    def clone(self):
        spc = ComputationSpace(NoProblem, parent=self)
        print "-- cloning %s to %s --" % (self.id, spc.id)
        self._notify(event.Clone)
        spc._propagate()
        return spc

    def commit(self, choice):
        """if self is distributable, causes the Choose call in the
           space to complete and return some_number as a result. This
           may cause the spzce to resume execution.
           some_number must satisfy 1=<I=<N where N is the first arg
           of the Choose call.
        """
        self.distributor.distribute(choice-1)

    def choose(self, nb_choices):
        """
        waits for stability
        blocks until commit provides a value
        between 0 and nb_choices
        at most one choose running in a given space
        at a given time
        ----
        this is used by the distributor
        """
    
    def merge(self):
        """binds root vars to their singleton domains """
        assert self.status == Succeeded
        # this can't work if we don't copy vars too
        #for var in self.root.val:
        #    var.bind(self.dom(var).get_values()[0])
        # shut down the distributor
        res = {}
        for var in self.root.val:
            res[var.name] = self.dom(var).get_values()[0]
        return res

    def set_distributor(self, dist):
        self.distributor = dist

    def inject(self, restricting_problem):
        """add additional entities into a space"""
        restricting_problem(self)
        self._notify(event.Clone)
        self._propagate()
        
#-- Constraint Store ---------------------------------------

    #-- Variables ----------------------------

    def var(self, name):
        """creates a single assignment variable of name name
           and puts it into the store"""
        #v = Var(name, self)
        v = Var(name=name)
        self.add_unbound(v, name)
        return v

    def bind(self, var, val): # kill me !
        var.bind(val)

    def make_vars(self, *names):
        variables = []
        for name in names:
            variables.append(self.var(name))
        return tuple(variables)

    def add_unbound(self, var, name):
        """add unbound variable to the store"""
        if var in self.vars:
            print "warning :", name, "is already in store"
        self.vars.add(var)
        self.names[name] = var
        print "just created new var %s" % var

    def find_var(self, name):
        """looks up one variable"""
        try:
            return self.names[name]
        except KeyError:
            raise NotInStore(name)

    def find_vars(self, *names):
        """looks up many variables"""
        try:
            return [self.names[name]
                    for name in names]
        except KeyError:
            raise NotInStore(str(names))

    def is_bound(self, var):
        """check wether a var has a singleton domain"""
        return len(self.dom(var)) == 1

    def val(self, var):
        """return the speculative"""
        if self.is_bound(var): 
            return self.dom(var)[0]
        return NoValue

    #-- Domains -----------------------------

    def set_dom(self, var, dom):
        """bind variable to domain"""
        assert(isinstance(var, Var) and (var in self.vars))
        if var.is_bound():
            print "warning : setting domain %s to bound var %s" \
                  % (dom, var)
        self.doms[var] = FiniteDomain(dom)

    def dom(self, var):
        assert isinstance(var, Var)
        return self.doms.get(var, NoDom)
        try:
            return self.doms[var]
        except KeyError:
            self.doms[var] = NoDom
            return NoDom


    def copy_domains(self, space):
        for var in self.vars:
            if space.dom(var) != NoDom:
                self.set_dom(var, space.dom(var).copy())
                assert space.dom(var) == self.dom(var)
                assert id(self.dom(var)) != id(space.dom(var))

    #-- Constraints -------------------------

    def _add_const(self, constraint):
        self.constraints.add(constraint)
        self._notify(event.Inject(constraint))
        for var in constraint.affected_variables():
            self.var_const_map.setdefault(var, set())
            self.var_const_map[var].add(constraint)

    def add_expression(self, constraint):
        self._add_const(constraint)
        
    def add_constraint(self, vars, const):
        constraint = Expression(self, vars, const)
        self._add_const(constraint)

    def dependant_constraints(self, var):
        return self.var_const_map[var]

    def get_variables_with_a_domain(self):
        varset = set()
        for var in self.vars:
            if self.dom(var) != NoDom: varset.add(var)
        return varset

    def copy_constraints(self, space):
        self.constraints = set()
        for const in space.constraints:
            self._add_const(const.copy_to(self))

    #-- Constraint propagation ---------------

    def _init_constraint_queue(self):
        cqueue = []
        init_const_set = set()
        for ev in self.event_set:
            if isinstance(ev, event.Revise):
                for const in self.var_const_map[ev.var]:
                    init_const_set.add(const)
            elif isinstance(ev, event.Inject):
                init_const_set.add(ev.constraint)
                
        cqueue = [(const.estimate_cost(), const)
                  for const in init_const_set]
        return cqueue

    def satisfy_all(self):
        """really PROPAGATE from AC3"""
        const_q = self._init_constraint_queue()
        assert const_q != []
        const_q.sort()
        affected_constraints = set()
        while True:
            if not const_q:
                const_q = [(const.estimate_cost(), const)
                           for const in affected_constraints]
                if not const_q:
                    break
                const_q.sort()
                affected_constraints.clear()
            cost, const = const_q.pop(0)
            entailed = const.revise()
            for var in const.affected_variables():
                dom = self.dom(var)
                if not dom.has_changed():
                    continue
                for dependant_const in self.dependant_constraints(var):
                    if dependant_const is not const:
                        affected_constraints.add(dependant_const)
                dom.reset_flags()
            if entailed:
                # we should also remove the constraint from
                # the set of satifiable constraints
                if const in affected_constraints:
                    affected_constraints.remove(const)
