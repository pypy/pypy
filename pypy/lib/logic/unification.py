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
## Unification as put in Oz is a very powerful operation. It is
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

from variable import EqSet, Var, VariableException, NotAVariable

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

class UnificationFailure(Exception):
    def __init__(self, var1, var2):
        self.var1, self.var2 = (var1, var2)
    def __str__(self):
        return "%s %s can't be unified" % (self.var1,
                                           self.var2)
              
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
        # set of all known vars
        self.vars = set()
        self.in_transaction = False

    def add_unbound(self, var):
        # register globally
        if var in self.vars:
            raise AlreadyInStore(var.name)
        print "adding %s to the store" % var
        self.vars.add(var)
        # put into new singleton equiv. set
        var.val = EqSet([var])

    #-- BIND -------------------------------------------

    def bind(self, var, val):
        """1. (unbound)Variable/(unbound)Variable or
           2. (unbound)Variable/(bound)Variable or
           3. (unbound)Variable/Value binding
        """
        assert(isinstance(var, Var) and (var in self.vars))
        if var == val:
            return
        if _both_are_vars(var, val):
            if _both_are_bound(var, val):
                raise AlreadyBound(var.name)
            if var.is_bound(): # 2b. var is bound, not var
                self.bind(val, var)
            elif val.is_bound(): # 2a.val is bound, not val
                self._bind(var.val, val.val)
            else: # 1. both are unbound
                self._merge(var.val, val.val)
        else: # 3. val is really a value
            if var.is_bound():
                raise AlreadyBound(var.name)
            self._bind(var.val, val)


    def _bind(self, eqs, val):
        print "variable - value binding : %s %s" % (eqs, val)
        # bind all vars in the eqset to obj
        for var in eqs:
            var.val = val

    def _merge(self, eqs1, eqs2):
        print "unbound variables binding : %s %s" % (eqs1, eqs2)
        if eqs1 == eqs2: return
        # merge two equisets into one
        eqs1 |= eqs2
        # let's reassign everybody to neweqs
        self._bind(eqs1, eqs1)

    #-- UNIFY ------------------------------------------

    def unify(self, x, y):
        self.in_transaction = True
        try:
            try:
                self._really_unify(x, y)
                for var in self.vars:
                    if var.changed:
                        var.commit()
            except:
                for var in self.vars:
                    if var.changed:
                        var.abort()
                raise
        finally:
            self.in_transaction = False

    def _really_unify(self, x, y):
        #FIXME in case of failure, the store state is not
        #      properly restored ...
        print "unify %s with %s" % (x,y)
        if not _unifiable(x, y): raise UnificationFailure(x, y)
        # dispatch to the apropriate unifier
        if not x in self.vars:
            if not y in self.vars:
                if x != y: raise UnificationFailure(x, y)
            self._unify_var_val(y, x)
        elif not y in self.vars:
            self._unify_var_val(x, y)
        elif _both_are_bound(x, y):
            self._unify_bound(x,y)
        elif x.isbound():
            self.bind(x,y)
        else:
            self.bind(y,x)

    def _unify_var_val(self, x, y):
        if x.is_bound(): raise UnificationFailure(x, y)
        if x != y:
            self.bind(x, y)
        
    def _unify_bound(self, x, y):
        print "unify bound %s %s" % (x, y)
        vx, vy = (x.val, y.val)
        if type(vx) in [list, set] and isinstance(vy, type(vx)):
            self._unify_iterable(x, y)
        elif type(vx) is dict and isinstance(vy, type(vx)):
            self._unify_mapping(x, y)
        else:
            raise UnificationFailure(x, y)

    def _unify_iterable(self, x, y):
        print "unify sequences %s %s" % (x, y)
        vx, vy = (x.val, y.val)
        idx, top = (0, len(vx))
        while (idx < top):
            self._really_unify(vx[idx], vy[idx])
            idx += 1

    def _unify_mapping(self, x, y):
        print "unify mappings %s %s" % (x, y)
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
    _unifiable_memo = set()
    return _really_unifiable(term1, term2)
        
def _really_unifiable(term1, term2):
    """Checks wether two terms can be unified"""
    if ((id(term1), id(term2))) in _unifiable_memo: return False
    _unifiable_memo.add((id(term1), id(term2)))
    print "unifiable ? %s %s" % (term1, term2)
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
   print "unifiable sequences ? %s %s" % (c1, c2)
   if len(c1) != len(c2): return False
   idx, top = (0, len(c1))
   while(idx < top):
       if not _really_unifiable(c1[idx], c2[idx]):
           return False
       idx += 1
   return True

def _mapping_unifiable(m1, m2):
    """Checks wether two mappings can be unified"""
    print "unifiable mappings ? %s %s" % (m1, m2)
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
    return v1.is_bound() and v2.is_bound()

#--
#-- the global store
_store = Store()

#-- global accessor functions
def var(name):
    v = Var(name, _store)
    _store.add_unbound(v)
    return v

def bind(var, val):
    return _store.bind(var, val)

def unify(var1, var2):
    return _store.unify(var1, var2)

def bound():
    return _store.bound.keys()

def unbound():
    res = []
    for cluster in _store.unbound:
        res.append('='.join([str(var) for var in cluster]))
    return res
