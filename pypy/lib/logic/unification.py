## Oz-like unification of dataflow variables in Python 2.4
## within a single assignment store
## crude ...

## Unification over dataflow variables in Oz is a powerful mechanism
## which is the basis of relational, logic and constraint programming.
## Please read the stuff in variable.py to understand the nature of
## dataflow variables.
##
## Unification in Oz (almost verbatim from CTM*)
## =============================================
##
## Unification as put in Oz is "a very powerful operation". It is
## provided through the '=' operator.
##
## Binding a variable to a value is a special case of an operation
## called unification. The unification <TERM1>=<TERM2> makes the
## partial values <TERM1> and <TERM2> equal, if possible, by adding
## zero or more bindings to the store. For example, f(X Y)=f(1 2) does
## two bindings: X=1 and Y=2. If the two terms cannot be made equal,
## then an exception is raised. Unification exists because of partial
## values; if there would be only complete values, then it would have
## no meaning.
##
## Unification adds information to the single-assignment store (a set
## of dataflow variables, where each variable is either unbound or
## bound to some other store entity).
##
## Example : if the store has X=foo(A) and Y=foo(25), then doing X=Y
## will bind A to 25.
##
## *failure* is the exception raised when unification cannot
## happen. For instance (unification of two records) :
##
##  person(name:X1 age:23)
##  person(name:"Auc" age:32)
##
## will raise it. The fail statement raises this exception.
##
## It is symetric : X=Y means the same as Y=X
## It can create cyclic structures, as in : X=person(grandfather:X)
## It can bind cyclic structures :
##
##  X=f(a:X b:_)
##  Y=f(a:_ b:Y)
##  X=Y
##
## creates a two cycles structure writable as : X=f(a:X b:X)
##
## Unification algorithm :
##
## operation unify(x, y) that unify two partial values x and y in the
## store st.
##
## The Store consists of a set of k variables : x1, ... xk that are
## partitioned as follows:
##
## * set of unbound variables that are equal (also called equivalence
##   sets of variables). The variables in each set are equal to each
##   other but not to any other variables.
##
## * variables bound to a number, record or procedure (also called
##   determined variables).
##
## Example : st = {x1=foo(a:x2), x2=25, x3=x4=x5, x6, x7=x8} that has
## 8 variables. It has three equivalence sets :
## {x3,x4,x5},{x6},{x7,x8}. It has two determined variables x1 and x2.
##
## The primitive bind operation : unification is defined in terms of a
## primitive bind operation on the store st. The operation binds all
## variables in an equivalence set:
##
## * bind(ES,<v>) binds all variables in the equivalence set ES to the
##   number or record <v>. For example, the operation
##   bind({x7,x8},foo(a:x2)) binds x7 and x8, which no longer are in
##   an equivalence set.
##
## * bind(ES1,ES2) merges the equivalence set ES1 with the equivalence
##   set ES2.
##
## Algorithm unify(x,y)
##
## 1. if x is in the equivalence set ESx and y is in the equivalence
##    set ESy, then do bind(ESx,ESy). It is a noop if ESx == ESy.
##
## 2. if x is in the equivalence set ESx and y is determined**, then do
##    bind(ESx,y)
##
## 3. if y is in the equivalence set ESy and y is determined, then do
##    bind(ESy,x)
##
## 4. if x is bound to l(l1:x1,...,ln:xn) and y is bound to
##    l'(l'1:y1,...,l'm:ym) with l!=l' or {l1,...,ln}!={l'1,...,l'm},
##    then raise a failure exception
##
## 5. if x is bound to l(l1:x1,...,ln:xn) and y is bound to
##    l(l1:y1,...,ln:yn), then for i from 1 to n do unify(xi,yi).
##
##
## With cycles : the above algorithm does not handle unification of
## partial values with cycles. For example, on x=f(a:x) and y=f(a:y) a
## call to unify(x,y) results in the recursive call unify(x,y), which
## is identical to the original call, looping forever.  A simple fix
## is to make sure that unify(x,y) is called at most once for each
## possible pair of two variables (x,y); We do this through
## memoization of called pairs.

## * CTM : Concepts, Techniques and Models of Computer Programming
## ** determined == bound

#TODO :
# * understand this :
#   http://www.mozart-oz.org/papers/abstracts/ProgrammingConstraintServices.html
# * support '_' as shown above
# * turn Var into some dataflow-ish thing (as far as Python allows)
# * ensure that the store supports concurrent access
#   (using the implicit blocking provided by dataflow vars)
# * add entailment checks
# * add constraints support

import threading

from variable import EqSet, Var, VariableException, NotAVariable
from constraint import FiniteDomain, ConsistencyFailure

#----------- Store Exceptions ----------------------------
class UnboundVariable(VariableException):
    def __str__(self):
        return "%s has no value yet" % self.name

class AlreadyBound(VariableException):
    def __str__(self):
        return "%s is already bound" % self.name

class AlreadyInStore(VariableException):
    def __str__(self):
        return "%s already in store" % self.name

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
    
#----------- Store ------------------------------------
class Store(object):
    """The Store consists of a set of k variables
       x1,...,xk that are partitioned as follows: 
       * set of unbound variables that are equal
         (also called equivalence sets of variables).
         The variables in each set are equal to each
         other but not to any other variables.
       * variables bound to a number, record or procedure
         (also called determined variables)."""
    
    def __init__(self):
        # mapping of names to vars (all of them)
        self.vars = set()
        self.names = set()
        # set of all constraints 
        self.constraints = set()
        # consistency-preserving stuff
        self.in_transaction = False
        self.lock = threading.RLock()

    #-- Variables ----------------------------

    def var(self, name):
        """creates a variable of name name and put
           it into the store"""
        v = Var(name, self)
        self.add_unbound(v)
        return v

    def add_unbound(self, var):
        """add unbound variable to the store"""
        if var in self.vars:
            raise AlreadyInStore(var.name)
        print "adding %s to the store" % var
        self.vars.add(var)
        self.names.add(var.name)
        # put into new singleton equiv. set
        var.val = EqSet([var])

    def set_domain(self, var, dom):
        """bind variable to domain"""
        assert(isinstance(var, Var) and (var in self.vars))
        if var.is_bound():
            raise AlreadyBound
        var.dom = FiniteDomain(dom)
    
    #-- Constraints -------------------------

    def add_constraint(self, constraint):
        self.constraints.add(constraint)

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
        compute_dependant_vars(constraint, varset, constset)
        old_domains = collect_domains(varset)
        
        for const in constset:
            try:
                const.narrow()
            except ConsistencyFailure:
                restore_domains(old_domains)
                return False
        restore_domains(old_domains)
        return True


    def get_satisfying_domains(self, constraint):
        assert constraint in self.constraints
        varset = set()
        constset = set()
        compute_dependant_vars(constraint, varset, constset)
        old_domains = collect_domains(varset)

        for const in constset:
            try:
                const.narrow()
            except ConsistencyFailure:
                restore_domains(old_domains)
                return {}
        narrowed_domains = collect_domains(varset)
        restore_domains(old_domains)
        return narrowed_domains

    def satisfy(self, constraint):
        assert constraint in self.constraints
        varset = set()
        constset = set()
        compute_dependant_vars(constraint, varset, constset)
        old_domains = collect_domains(varset)

        for const in constset:
            try:
                const.narrow()
            except ConsistencyFailure:
                restore_domains(old_domains)
                raise
        
        
    #-- BIND -------------------------------------------

    def bind(self, var, val):
        """1. (unbound)Variable/(unbound)Variable or
           2. (unbound)Variable/(bound)Variable or
           3. (unbound)Variable/Value binding
        """
        try:
            self.lock.acquire()
            assert(isinstance(var, Var) and (var in self.vars))
            if var == val:
                return
            if _both_are_vars(var, val):
                if _both_are_bound(var, val):
                    raise AlreadyBound(var.name)
                if var._is_bound(): # 2b. var is bound, not var
                    self.bind(val, var)
                elif val._is_bound(): # 2a.var is bound, not val
                    self._bind(var.val, val.val)
                else: # 1. both are unbound
                    self._merge(var, val)
            else: # 3. val is really a value
                print "%s, is that you ?" % var
                if var._is_bound():
                    raise AlreadyBound(var.name)
                self._bind(var.val, val)
        finally:
            self.lock.release()


    def _bind(self, eqs, val):
        # print "variable - value binding : %s %s" % (eqs, val)
        # bind all vars in the eqset to val
        for var in eqs:
            if var.dom != None:
                if val not in var.dom.get_values():
                    # undo the half-done binding
                    for v in eqs:
                        v.val = eqs
                    raise OutOfDomain(var)
            var.val = val

    def _merge(self, v1, v2):
        for v in v1.val:
            if not _compatible_domains(v, v2.val):
                raise IncompatibleDomains(v1, v2)
        self._really_merge(v1.val, v2.val)

    def _really_merge(self, eqs1, eqs2):
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
                    if var.changed:
                        var._commit()
            except Exception, cause:
                for var in self.vars:
                    if var.changed:
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
        if x.val != y:
            try:
                self.bind(x, y)
            except AlreadyBound:
                raise UnificationFailure(x, y)
        
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
        print "unify sequences %s %s" % (x, y)
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


def _compatible_domains(var, eqs):
    """check that the domain of var is compatible
       with the domains of the vars in the eqs
    """
    if var.dom == None: return True
    empty = set()
    for v in eqs:
        if v.dom == None: continue
        if v.dom.intersection(var.dom) == empty:
            return False
    return True


def compute_dependant_vars(constraint, varset,
                           constset):
    if constraint in constset: return
    constset.add(constraint)
    for var in constraint.affectedVariables():
        varset.add(var)
        dep_consts = var.constraints
        for const in dep_consts:
            if const in constset:
                continue
            compute_dependant_vars(const, varset, constset)


#-- collect / restore utilities for domains

def collect_domains(varset):
    """makes a copy of domains of a set of vars
       into a var -> dom mapping
    """
    dom = {}
    for var in varset:
        dom[var] = FiniteDomain(var.dom)
    return dom

def restore_domains(domains):
    """sets the domain of the vars in the domains mapping
       to their (previous) value 
    """
    for var, dom in domains.items():
        var.dom = dom


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

#-- Some utilities -----------------------------------------------

def _both_are_vars(v1, v2):
    return isinstance(v1, Var) and isinstance(v2, Var)
    
def _both_are_bound(v1, v2):
    return v1._is_bound() and v2._is_bound()

#--
#-- the global store
_store = Store()

#-- global accessor functions
def var(name):
    v = Var(name, _store)
    _store.add_unbound(v)
    return v

def set_domain(var, dom):
    return _store.set_domain(var, dom)

def add_constraint(constraint):
    return _store.add_constraint(constraint)

def satisfiable(constraint):
    return _store.satisfiable(constraint)

def get_satisfying_domains(constraint):
    return _store.get_satisfying_domains(constraint)

def satisfy(constraint):
    return _store.satisfy(constraint)

def bind(var, val):
    return _store.bind(var, val)

def unify(var1, var2):
    return _store.unify(var1, var2)

def bound():
    return map(_store.vars,
               lambda v: v.is_bound())

def unbound():
    return map(_store.vars,
               lambda v: not v.is_bound())
