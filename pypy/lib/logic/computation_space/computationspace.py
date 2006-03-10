# TODO
# * [1] adapt other distribution strategies
# * [5] add a linear constraint solver (vital for fast
#   constraint propagation over finite integer domains)
#   and other kinds of specialized propagators

from threading import Thread, Condition, RLock, local

from state import Succeeded, Failed, Unknown

from variable import EqSet, CsVar, NoValue, NoDom, \
     VariableException, NotAVariable, AlreadyInStore, \
     AlreadyBound
from constraint import FiniteDomain, ConsistencyFailure, \
     Expression
from distributor import DefaultDistributor
import event # NewSpace, Clone, Revise

class Alternative(object):

    def __init__(self, choices):
        self._choices = choices

    def __eq__(self, other):
        if other is None: return False
        if not isinstance(other, Alternative): return False
        return self._choices == other._choices

    def __str__(self):
        return "Alternatives(%s)" % self._choices

def NoProblem():
    """the empty problem, used by clone()"""
    pass
        
#----------- Store Exceptions ----------------------------
class UnboundVariable(VariableException):
    def __str__(self):
        return "%s has no value yet" % self.name

class AlreadyBound(VariableException):
    def __str__(self):
        return "%s is already bound" % self.name

class NotInStore(VariableException):
    def __str__(self):
        return "%s not in the store" % self.name

class OutOfDomain(VariableException):
    def __str__(self):
        return "value not in domain of %s" % self.name

class UnificationFailure(Exception):
    def __init__(self, var1, var2, cause=None):
        self.var1, self.var2 = (var1, var2)
        self.cause = cause
    def __str__(self):
        diag = "%s %s can't be unified"
        if self.cause:
            diag += " because %s" % self.cause
        return diag % (self.var1, self.var2)
        
class IncompatibleDomains(Exception):
    def __init__(self, var1, var2):
        self.var1, self.var2 = (var1, var2)
    def __str__(self):
        return "%s %s have incompatible domains" % \
               (self.var1, self.var2)
    
#---- ComputationSpace -------------------------------
class ComputationSpace(object):

    # we have to enforce only one distributor
    # thread running in one space at the same time
    _nb_choices = 0
    _id_count = 0

    def __init__(self, problem, parent=None):
        self.id = ComputationSpace._id_count
        ComputationSpace._id_count += 1
        self.status = Unknown
        # consistency-preserving stuff
        self.in_transaction = False
        self.bind_lock = RLock()
        self.var_lock = RLock()
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
            self.status = Unknown
            self.distributor = parent.distributor.__class__(self)

#-- utilities & instrumentation -----------------------------

    def __str__(self):
        ret = ["<space:\n"]
        for v, d in self.doms.items():
            if self.dom(v) != NoDom:
                ret.append('  ('+str(v)+':'+str(d)+')\n')
        ret.append(">")
        return ' '.join(ret)

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

    def top_level(self):
        return self.parent is None

    def _notify(self, event):
        self.event_set.add(event)

    #-- space official API ------------------------------------

    def ask(self):
        self._propagate()
        if self.status in (Failed, Succeeded):
            return self.status
        if self._distributable():
            return Alternative(self.distributor.nb_subdomains())

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
        this is used by the distributor thread
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
        self._propagate()

        
#-- Constraint Store ---------------------------------------

    #-- Variables ----------------------------

    def var(self, name):
        """creates a single assignment variable of name name
           and puts it into the store"""
        self.var_lock.acquire()
        try:
            v = CsVar(name, self)
            self.add_unbound(v)
            return v
        finally:
            self.var_lock.release()

    def make_vars(self, *names):
        variables = []
        for name in names:
            variables.append(self.var(name))
        return tuple(variables)

    def add_unbound(self, var):
        """add unbound variable to the store"""
        if var in self.vars:
            raise AlreadyInStore(var.name)
        #print "adding %s to the store" % var
        self.vars.add(var)
        self.names[var.name] = var
        # put into new singleton equiv. set
        var.val = EqSet([var])

    def get_var_by_name(self, name):
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
        """check wether a var is locally bound"""
        if self.top_level():
            return var.is_bound()
        return len(self.dom(var)) == 1

    def val(self, var):
        """return the local binding without blocking"""
        if self.top_level(): # the real thing
            return var.val
        if self.is_bound(var): # the speculative val
            return self.dom(var)[0]
        return NoValue

    def _del_var(self, var):
        """purely private stuff, use at your own perils"""
        self.vars.remove(var)
        if self.doms.has_key(var):
            del self.doms[var]

    #-- Domains -----------------------------

    def set_dom(self, var, dom):
        """bind variable to domain"""
        assert(isinstance(var, CsVar) and (var in self.vars))
        if var.is_bound():
            print "warning : setting domain %s to bound var %s" \
                  % (dom, var)
        self.doms[var] = FiniteDomain(dom)

    def dom(self, var):
        assert isinstance(var, CsVar)
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

    def add_distributed(self, var):
        self.changelog.append(var)

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
        """really PROPAGATE"""
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
            entailed = const.revise3()
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
                    
    def _compute_dependant_vars(self, constraint, varset,
                               constset):
        if constraint in constset: return
        constset.add(constraint)
        for var in constraint.affected_variables():
            varset.add(var)
            dep_consts = self.var_const_map[var]
            for const in dep_consts:
                if const in constset:
                    continue
                self._compute_dependant_vars(const, varset,
                                            constset)

    def _compatible_domains(self, var, eqs):
        """check that the domain of var is compatible
           with the domains of the vars in the eqs
        """
        if self.dom(var) == NoDom: return True
        empty = set()
        for v in eqs:
            if self.dom(v) == NoDom: continue
            if self.dom(v).intersection(self.dom(var)) == empty:
                return False
        return True

    #-- collect / restore utilities for domains

    def collect_domains(self, varset):
        """makes a copy of domains of a set of vars
           into a var -> dom mapping
        """
        dom = {}
        for var in varset:
            if self.dom(var) != NoDom:
                dom[var] = self.dom(var).copy()
        return dom

    def restore_domains(self, domains):
        """sets the domain of the vars in the domains mapping
           to their (previous) value 
        """
        for var, dom in domains.items():
            self.set_dom(var, dom)

        
    #-- BIND -------------------------------------------

    def bind(self, var, val):
        """1. (unbound)Variable/(unbound)Variable or
           2. (unbound)Variable/(bound)Variable or
           3. (unbound)Variable/Value binding
        """
        # just introduced complete dataflow behaviour,
        # where binding several times to compatible
        # values is allowed provided no information is
        # removed (this last condition remains to be checked)
        self.bind_lock.acquire()
        try:
            assert(isinstance(var, CsVar) and (var in self.vars))
            if var == val:
                return
            if _both_are_vars(var, val):
                if _both_are_bound(var, val):
                    if _unifiable(var, val):
                        return # XXX check corrrectness
                    raise UnificationFailure(var, val)
                if var._is_bound(): # 2b. var is bound, not var
                    self.bind(val, var)
                elif val._is_bound(): # 2a.var is bound, not val
                    self._bind(var.val, val.val)
                else: # 1. both are unbound
                    self._alias(var, val)
            else: # 3. val is really a value
                if var._is_bound():
                    if _unifiable(var.val, val):
                        return # XXX check correctness
                    raise UnificationFailure(var, val)
                self._bind(var.val, val)
        finally:
            self.bind_lock.release()

    def _bind(self, eqs, val):
        # print "variable - value binding : %s %s" % (eqs, val)
        # bind all vars in the eqset to val
        for var in eqs:
            if self.dom(var) != NoDom:
                if val not in self.dom(var).get_values():
                    # undo the half-done binding
                    for v in eqs:
                        v.val = eqs
                    raise OutOfDomain(var)
            var.val = val

    def _alias(self, v1, v2):
        for v in v1.val:
            if not self._compatible_domains(v, v2.val):
                raise IncompatibleDomains(v1, v2)
        self._really_alias(v1.val, v2.val)

    def _really_alias(self, eqs1, eqs2):
        # print "unbound variables binding : %s %s" % (eqs1, eqs2)
        if eqs1 == eqs2: return
        # merge two equisets into one
        eqs1 |= eqs2
        # let's reassign everybody to the merged eq
        for var in eqs1:
            var.val = eqs1

    #-- UNIFY ------------------------------------------

    def unify(self, x, y):
        self.in_transaction = True
        try:
            try:
                self._really_unify(x, y)
                for var in self.vars:
                    if var._changed:
                        var._commit()
            except Exception, cause:
                for var in self.vars:
                    if var._changed:
                        var._abort()
                if isinstance(cause, UnificationFailure):
                    raise
                raise UnificationFailure(x, y, cause)
        finally:
            self.in_transaction = False

    def _really_unify(self, x, y):
        # print "unify %s with %s" % (x,y)
        if not _unifiable(x, y): raise UnificationFailure(x, y)
        if not x in self.vars:
            if not y in self.vars:
                # duh ! x & y not vars
                if x != y: raise UnificationFailure(x, y)
                else: return
            # same call, reverse args. order
            self._unify_var_val(y, x)
        elif not y in self.vars:
            # x is Var, y a value
            self._unify_var_val(x, y)
        elif _both_are_bound(x, y):
            self._unify_bound(x,y)
        elif x._is_bound():
            self.bind(x,y)
        else:
            self.bind(y,x)

    def _unify_var_val(self, x, y):
        if x.val != y: # what else ?
            self.bind(x, y)
        
    def _unify_bound(self, x, y):
        # print "unify bound %s %s" % (x, y)
        vx, vy = (x.val, y.val)
        if type(vx) in [list, set] and isinstance(vy, type(vx)):
            self._unify_iterable(x, y)
        elif type(vx) is dict and isinstance(vy, type(vx)):
            self._unify_mapping(x, y)
        else:
            if vx != vy:
                raise UnificationFailure(x, y)

    def _unify_iterable(self, x, y):
        #print "unify sequences %s %s" % (x, y)
        vx, vy = (x.val, y.val)
        idx, top = (0, len(vx))
        while (idx < top):
            self._really_unify(vx[idx], vy[idx])
            idx += 1

    def _unify_mapping(self, x, y):
        # print "unify mappings %s %s" % (x, y)
        vx, vy = (x.val, y.val)
        for xk in vx.keys():
            self._really_unify(vx[xk], vy[xk])

#-- Unifiability checks---------------------------------------
#--
#-- quite costly & could be merged back in unify

def _iterable(thing):
    return type(thing) in [tuple, frozenset]

def _mapping(thing):
    # should be frozendict (python 2.5 ?)
    return isinstance(thing, dict)

# memoizer for _unifiable
_unifiable_memo = set()

def _unifiable(term1, term2):
    global _unifiable_memo
    _unifiable_memo = set()
    return _really_unifiable(term1, term2)
        
def _really_unifiable(term1, term2):
    """Checks wether two terms can be unified"""
    if ((id(term1), id(term2))) in _unifiable_memo: return False
    _unifiable_memo.add((id(term1), id(term2)))
    # print "unifiable ? %s %s" % (term1, term2)
    if _iterable(term1):
        if _iterable(term2):
            return _iterable_unifiable(term1, term2)
        return False
    if _mapping(term1) and _mapping(term2):
        return _mapping_unifiable(term1, term2)
    if not(isinstance(term1, CsVar) or isinstance(term2, CsVar)):
        return term1 == term2 # same 'atomic' object
    return True
        
def _iterable_unifiable(c1, c2):
   """Checks wether two iterables can be unified"""
   # print "unifiable sequences ? %s %s" % (c1, c2)
   if len(c1) != len(c2): return False
   idx, top = (0, len(c1))
   while(idx < top):
       if not _really_unifiable(c1[idx], c2[idx]):
           return False
       idx += 1
   return True

def _mapping_unifiable(m1, m2):
    """Checks wether two mappings can be unified"""
    # print "unifiable mappings ? %s %s" % (m1, m2)
    if len(m1) != len(m2): return False
    if m1.keys() != m2.keys(): return False
    v1, v2 = (m1.items(), m2.items())
    v1.sort()
    v2.sort()
    return _iterable_unifiable([e[1] for e in v1],
                               [e[1] for e in v2])

#-- Some utilities -------------------------------------------

def _both_are_vars(v1, v2):
    return isinstance(v1, CsVar) and isinstance(v2, CsVar)
    
def _both_are_bound(v1, v2):
    return v1._is_bound() and v2._is_bound()

def diff_list(l1, l2):
    diff = {}
    idx = 0
    for e1, e2 in zip(l1, l2):
        if e1 != e2: diff[idx] = (e1, e2)
        idx += 1
    return diff

def backup_domains(space):
    print "-- backup of domains (%s) --" % space.id
    doms = []
    for v, d in space.doms.items():
        if d != NoDom:
            doms.append((v, len(d)))
    doms.sort()
    print "  (", [elt[1] for elt in doms], ")"
    return doms

def print_quick_diff(space, domain_history):
    ldh = len(domain_history)
    if ldh > 0:
        print "history size (%s) : %s" % (space.id, ldh)
        last = domain_history[-1]
    else:
        curr = [(item[0], len(item[1].get_values()))
                for item in space.doms.items()
                if item[1] != NoDom]
        curr.sort()
        print "(diff -- v : d 0        (%s)" % space.id
        for l in curr:
            print ' '*6, '%s :  %2d' % (l[0], l[1]) 
        print " --)"
        return
    curr = [(item[0], len(item[1].get_values()))
            for item in space.doms.items()
            if item[1] != NoDom]
    curr.sort()
    print "(diff -- v : d%2d | d%2d (%s)" % (ldh, ldh+1, space.id)
    for l1, l2 in zip(last, curr):
        print ' '*6, '%s :  %2d | %2d ' % (l1[0], l1[1], l2[1]) 
    print " --)"
