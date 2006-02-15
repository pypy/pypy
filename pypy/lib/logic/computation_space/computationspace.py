from threading import Thread, Condition, RLock, local

from state import Succeeded, Distributable, Failed, \
     Merged, Distributing

from variable import EqSet, Var, NoValue, Pair, \
     VariableException, NotAVariable, AlreadyInStore
from constraint import FiniteDomain, ConsistencyFailure
from distributor import DefaultDistributor

EmptyDom = FiniteDomain([])

class Alternatives(object):

    def __init__(self, nb_alternatives):
        self._nbalt = nb_alternatives

    def __eq__(self, other):
        if other is None: return False
        if not isinstance(other, Alternatives): return False
        return self._nbalt == other._nbalt

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

    def __init__(self, problem, parent=None):
        # consistency-preserving stuff
        self.in_transaction = False
        self.bind_lock = RLock()
        self.var_lock = RLock()
        self.status = None
        self.status_condition = Condition()
        self.distributor = DefaultDistributor(self)
        self.TOP = False
        
        if parent is None:
            self.TOP = True
            self.vars = set()
            # mapping of names to vars (all of them)
            self.names = {}
            # mapping of vars to constraints
            self.var_const_map = {}
            # set of all constraints 
            self.constraints = set()
            self.root = self.var('__root__')
            # set up the problem
            self.bind(self.root, problem(self))
            # check satisfiability of the space
            self._init_choose_commit()
            self._process()
            if self.status == Distributable:
                self.distributor.start()
        else:
            self.vars = parent.vars
            self.names = parent.names
            self.var_const_map = parent.var_const_map
            self.constraints = parent.constraints
            self.root = parent.root
            self._init_choose_commit()

    def _init_choose_commit(self):
        # create a unique choice point
        # using two vars as channels betwen
        # space and distributor threads
        self.CHOOSE = self._make_choice_var()
        self.STABLE = self._make_stable_var()
        # we start stanle
        self.STABLE.bind(0)

#-- Computation Space -----------------------------------------

    def _make_choice_var(self):
        ComputationSpace._nb_choices += 1
        return self.var('__choice__'+str(self._nb_choices))

    def _make_stable_var(self):
        ComputationSpace._nb_choices += 1
        return self.var('__stable__'+str(self._nb_choices))

    def _process(self):
        """auxilary of the distributor
           XXX: shouldn't only the distributor call it ?
        """
        try:
            self.satisfy_all()
        except ConsistencyFailure:
            self.status = Failed
        else:
            if self._distributable():
                self.status = Distributable
            else:
                self.status = Succeeded

    def _suspended(self):
        raise NotImplemented
        # additional basic constraints done in an ancestor can
        # make it runnable ; it is a temporary condition due
        # to concurrency ; it means that some ancestor space
        # has not yet transferred all required information to
        # the space 
    

    def _distributable(self):
        if self.status not in (Failed, Succeeded, Merged):
            # sync. barrier with distributor
            for var in self.vars:
                if var.cs_get_dom(self).size() > 1 :
                    return True
        return False
        # in The Book : "the space has one thread that is
        # suspended on a choice point with two or more alternatives.
        # A space can have at most one choice point; attempting to
        # create another gives an error."

    def ask(self):
        print "SPACE Ask() checks stability ..."
        self.STABLE.get() # that's real stability
        print "SPACE is stable, resuming Ask()"
        status = self.status in (Failed, Succeeded, Merged)
        if status: return self.status
        if self._distributable():
            return Alternatives(self.distributor.nb_subdomains())
        # should be unreachable
        raise NotImplemented

    def clone(self):
        #XXX: lazy copy of domains would be nice
        spc = ComputationSpace(NoProblem, parent=self)
        for var in spc.vars:
            var.cs_set_dom(spc, var.cs_get_dom(self).copy())
        spc.distributor.set_space(spc)
        if spc.status == Distributable:
            spc.distributor.start()
        return spc

    def inject(self, restricting_problem):
        """add additional entities into a space"""
        restricting_problem(self)
        self._process()

    def commit(self, choice):
        """if self is distributable, causes the Choose call in the
           space to complete and return some_number as a result. This
           may cause the spzce to resume execution.
           some_number must satisfy 1=<I=<N where N is the first arg
           of the Choose call.
        """
        print "SPACE commited to", choice
        # block future calls to Ask until the distributor
        # binds STABLE
        self.STABLE = self._make_stable_var()
        print "SPACE binds CHOOSE to", choice
        self.bind(self.CHOOSE, choice)


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
        choice = self.CHOOSE.get()
        return choice    

    def merge(self):
        """binds root vars to their singleton domains """
        assert self.status == Succeeded
        for var in self.root.val:
            var.bind(var.cs_get_dom(self).get_values()[0])
        self.status = Merged
        # shut down the distributor
        self.distributor.cs = None
        self.CHOOSE.bind(0)
        return self.root.val

    def set_distributor(self, dist):
        self.distributor = dist
        
#-- Constraint Store ---------------------------------------

    #-- Variables ----------------------------

    def var(self, name):
        """creates a single assignment variable of name name
           and puts it into the store"""
        self.var_lock.acquire()
        try:
            v = Var(name, self)
            self.add_unbound(v)
            return v
        finally:
            self.var_lock.release()

    def add_unbound(self, var):
        """add unbound variable to the store"""
        if var in self.vars:
            raise AlreadyInStore(var.name)
        #print "adding %s to the store" % var
        self.vars.add(var)
        self.names[var.name] = var
        # put into new singleton equiv. set
        var.val = EqSet([var])

    def set_domain(self, var, dom):
        """bind variable to domain"""
        assert(isinstance(var, Var) and (var in self.vars))
        if var.is_bound():
            raise AlreadyBound
        var.cs_set_dom(self, FiniteDomain(dom))

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
        if self.TOP:
            return var.is_bound()
        return len(var.cs_get_dom(self)) == 1

    def dom(self, var):
        """return the local domain"""
        return var.cs_get_dom(self)

    def val(self, var):
        """return the local binding without blocking"""
        if self.TOP: # the real thing
            return var.val
        if self.is_bound(var): # the speculative val
            return self.dom(var)[0]
        return NoValue
    
    #-- Constraints -------------------------

    def add_constraint(self, constraint):
        self.constraints.add(constraint)
        for var in constraint.affectedVariables():
            self.var_const_map.setdefault(var, [])
            self.var_const_map[var].append(constraint)

    def get_variables_with_a_domain(self):
        varset = set()
        for var in self.vars:
            if var.cs_get_dom(self) != EmptyDom: varset.add(var)
        return varset

    def satisfiable(self, constraint):
        """ * satisfiable (k) checks that the constraint k
              can be satisfied wrt its variable domains
              and other constraints on these variables
            * does NOT mutate the store
        """
        # Satisfiability of one constraints entails
        # satisfiability of the transitive closure
        # of all constraints associated with the vars
        # of our given constraint.
        # We make a copy of the domains
        # then traverse the constraints & attached vars
        # to collect all (in)directly affected vars
        # then compute narrow() on all (in)directly
        # affected constraints.
        assert constraint in self.constraints
        varset = set()
        constset = set()
        self._compute_dependant_vars(constraint, varset, constset)
        old_domains = self.collect_domains(varset)
        
        for const in constset:
            try:
                const.narrow()
            except ConsistencyFailure:
                self.restore_domains(old_domains)
                return False
        self.restore_domains(old_domains)
        return True


    def get_satisfying_domains(self, constraint):
        assert constraint in self.constraints
        varset = set()
        constset = set()
        self._compute_dependant_vars(constraint, varset,
                                     constset)
        old_domains = self.collect_domains(varset)
        
        for const in constset:
            try:
                const.narrow()
            except ConsistencyFailure:
                self.restore_domains(old_domains)
                return {}
        narrowed_domains = self.collect_domains(varset)
        self.restore_domains(old_domains)
        return narrowed_domains

    def satisfy(self, constraint):
        """narrows the domains down to satisfiability"""
        assert constraint in self.constraints
        varset = set()
        constset = set()
        self._compute_dependant_vars(constraint, varset, constset)
        old_domains = self.collect_domains(varset)

        for const in constset:
            try:
                const.narrow()
            except ConsistencyFailure:
                self.restore_domains(old_domains)
                raise

    def satisfy_all(self):
        old_domains = self.collect_domains(self.vars)
        for const in self.constraints:
            try:
                const.narrow()
            except ConsistencyFailure:
                self.restore_domains(old_domains)
                raise
                
    def _compute_dependant_vars(self, constraint, varset,
                               constset):
        if constraint in constset: return
        constset.add(constraint)
        for var in constraint.affectedVariables():
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
        if var.cs_get_dom(self) == EmptyDom: return True
        empty = set()
        for v in eqs:
            if v.cs_get_dom(self) == EmptyDom: continue
            if v.cs_get_dom(self).intersection(var.cs_get_dom(self)) == empty:
                return False
        return True

    #-- collect / restore utilities for domains

    def collect_domains(self, varset):
        """makes a copy of domains of a set of vars
           into a var -> dom mapping
        """
        dom = {}
        for var in varset:
            if var.cs_get_dom(self) != EmptyDom:
                dom[var] = var.cs_get_dom(self).copy()
        return dom

    def restore_domains(self, domains):
        """sets the domain of the vars in the domains mapping
           to their (previous) value 
        """
        for var, dom in domains.items():
            var.cs_set_dom(self, dom)

        
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
            assert(isinstance(var, Var) and (var in self.vars))
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
            if var.cs_get_dom(self) != EmptyDom:
                if val not in var.cs_get_dom(self).get_values():
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
    return type(thing) in [list, set]

def _mapping(thing):
    return type(thing) is dict

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
    if not(isinstance(term1, Var) or isinstance(term2, Var)):
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
    return isinstance(v1, Var) and isinstance(v2, Var)
    
def _both_are_bound(v1, v2):
    return v1._is_bound() and v2._is_bound()
