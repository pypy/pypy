# The Constraint-based computation model
## ======================================

## A computation space collects together basic constraints (in fact
## variable domains) and propagators (aka constraints), and puts them
## inside an encapsulation boundary. A propagator is simply a thread that
## can add new basic constraints to the store. A computation space is
## always created inside a parent space; it can see the constraints of
## its parent.

## Basic constraints and propagators
## ---------------------------------

## Basic constraints are constraints that are directly represented in the
## single-assignment store. An example of a basic constraint is a binding
## of a dataflow variable, such as x = person(age:y). This gives partial
## information about x. (SEE CHAPTER 2) The binding represents an
## equality constraint between the dataflow variable and a partial value.

## Here, we extend the store with a new kind of basic constraint, namely
## membership in a finite domain. A finite domain is a finite set of
## integers. The new basic constraint is an equation of the form x in D,
## where D is a finite domain. This gives partial information about
## x. This basic constraint is added to the store by the statement
## x::D. Note that the finite domain constraint x in {n} is equivalent to
## the binding x=n.

## Adding the constraints x::D1, x::D2, ..., x::Dn restricts the domain
## of x to the intersection of the n domains, provided that the latter is
## nonempty. Adding a constraint with an empty domain for a variable
## would result in an inconsistent store.

## The single-assignment store seen previously can be considered as a
## constraint store. The basic constraints it represent are all of the
## form x=y, where x and y are partial values. We call these constraints
## 'bindings', althhough they can do more than simply bind a variable to
## a value. The general operation of binding two partial values together
## is called unification.

## What are all the complete values to which a fresh variable can be
## bound ? This is not an obvious question since we can add cyclic
## bindings to the store, e.g X=foo(X). It turns out that variable can be
## bound to rational trees. A rational tree generalizes the finite trees
## to allow a certain kind of infinite trees that can be stored in a
## finite space. A rational tree can be represented as a root directed
## graph. Unfolding the graph to remove cycles and sharing yields the
## tree. For example the graph X=foo(X) represents the tree
## X=foo(foo(...)).

## When a variable is initially declared, it can potentially be bound to
## any rational tree. Each basic constraint (i.e each binding) that we
## add to the store restricts the set of rational trees to which the
## variable can be bound. For example, adding the constraint
## x=person(age:y) restricts the possible bindings of x, namely to
## rational trees whose root is a record of label person with one field
## whose feature name is age.  The single-assignment store therefore
## implements constraints over rational trees.

## The set of complete values to which a variable can be bound is called
## its domain. We talk here about constraints over two domains: rational
## trees and finite domains (the Mozart system implements finite sets of
## integer, fine-grained records and real interval).

## A propagator is a thread that continually observes the store and
## occasionally adds new basic constraints to the store. Each time a
## variable's domain is changes into the store, the propagators that use
## that variable must be given a chance to execute, so they can propagate
## new partial information ot variables. Wainting for a domain change is
## fine-grained variant of waiting for determinacy.

## The execution of these propagators must be order-independant.

## Programming searches with computation spaces
## --------------------------------------------

## We outline how computation spaces are used to implement search and
## distribution strategies. A search strategy defines how the search tree
## is explored (ie breadth-first,...). A distribution strategy defines
## the shape and content of the search tree, i.e how many alternatives
## exist at a node and what constraint is added for each
## alternative. Computation spaces can be used to program search
## strategies and distribution strategies independant of each other. How
## it is done :

## * create the space with the correct program inside. This program
##   defines all the variable and constraints in the space.

## * let the program run into the space. Variables and propagators are
##   created. All propagators execute until no more information can be
##   added to the store in this manner. The space eventually reaches
##   stability.

## * during the space's execution, the computation inside the space can
##   decide to create a choice point. The decision of which constraint to
##   add for each alternative defines the distribution strategy. One of
##   the space's thread will suspend when the choice point is created.

## * when the space has become stable, execution continues outside the
##   space, to decide what to do next. There are different possibilities
##   depending on whether or not a choice point has been created in that
##   space. If there is none, then execution can stop and return with a
##   solution. If there is one, then the search strategy decides which
##   alternative to choose and commits to that alternative.

## Refinement
## ============

## a computation space is made of :

## * a single assignment store
## * a thread store
## * a mutable store

## operations are :

## * newspace (creation)
## * wait_stable
## * choose
## * ask
## * commit
## * clone
## * inject
## * merge

## Newspace
## --------

## newspace p : when given a one-argument procedure p, creates a new
## computation space and returns a reference to it. In this space, a
## fresh root variable r and a new thread are created, and p(r) is
## invoked in the thread.

## There is always a top-level computatio space where threads may
## interact with the 'external' world.

## Wait_stable
## -----------

## Waits until the current space becomes stable.

## Choose
## ------

## Y=choose(N) waits until the current space becomes stable, blocks
## the current thread, and then creates a choice point with N
## alternatives in the current space. The blocked choose call waits
## for an alternative to be chosen by a commit operation on the
## space. The choose call only defines how many alternatives there
## are; it does not specify what to do for an alternative. Eventually,
## choose continues its execution with Y=I when alternative I
## (1=<I=<N) is chosen. A maximum of one choice point may exist in a
## space at any time.

## Ask
## ---

## A=Ask(s) asks the space s about its status. As soon as the space
## becomes stable, A is bound. If s if failed (merged, succeeded),
## then ask returns failed (merged, succeded). If s is distributable,
## then it returns alternatives(N), where N is the number of
## alternatives.

## An example specifying how to use a computation space :

## def my_problem(store):
##     #declare variables, their domain
##     x, y, z = var('x'), var('y'), var('z')
##     #declare constraints
##     set_domain(x, FiniteDomain([1, 2]))
##     set_domain(y, FiniteDomain([2, 3]))
##     set_domain(z, FiniteDomain([42, 43]))
##     add_constraint(c.Expression([x, y, z], 'x == y + z'))
##     add_constraint(c.Expression([z, w], 'z < w'))
##     #set up a distribution strategy
##     ????
##     return (x, y, z) 

## space = ComputationSpace(fun=my_problem)

from threading import Thread, Condition, RLock, local

from state import Succeeded, Distributable, Failed, Merged

from variable import EqSet, Var, \
     VariableException, NotAVariable, AlreadyInStore
from constraint import FiniteDomain, ConsistencyFailure
from distributor import DefaultDistributor


EmptyDom = FiniteDomain([])


class Alternatives(object):

    def __init__(self, nb_alternatives):
        self._nbalt = nb_alternatives

    def __eq__(self, other):
        if other is None: return False
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
    """The Store consists of a set of k variables
       x1,...,xk that are partitioned as follows: 
       * set of unbound variables that are equal
         (also called equivalence sets of variables).
         The variables in each set are equal to each
         other but not to any other variables.
       * variables bound to a number, record or procedure
         (also called determined variables)."""

    _nb_choices = 0

    
    def __init__(self, problem, parent=None):
        # consistency-preserving stuff
        self.in_transaction = False
        self.bind_lock = RLock()
        self.status = None
        self.status_condition = Condition()
        self.distributor = DefaultDistributor(self)
        
        if parent is None:
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
            self._process()
            if self.status == Distributable:
                self.distributor.start()
        else:
            self.vars = parent.vars
            self.names = parent.names
            self.var_const_map = parent.var_const_map
            self.constraints = parent.constraints
            self.root = parent.root

        # create a unique choice point
        self.CHOICE = self._make_choice_var()

    def __del__(self):
        self.status = Failed
        self.bind(self.CHOICE, 0)
        
#-- Store ------------------------------------------------

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
        try:
            return self.names[name]
        except KeyError:
            raise NotInStore(name)
    
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
        try:
            self.bind_lock.acquire()
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

    def _merge(self, v1, v2):
        for v in v1.val:
            if not self._compatible_domains(v, v2.val):
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

#-- Computation Space -----------------------------------------


    def _process(self):
        try:
            self.satisfy_all()
        except ConsistencyFailure:
            self.status = Failed
        else:
            if self._distributable():
                self.status = Distributable
            else:
                self.status = Succeeded

    def _stable(self):
        #XXX: really ?
        return self.status in (Failed, Succeeded, Merged) \
               or self._distributable()

    def _suspended(self):
        pass
        # additional basic constraints done in an ancestor can
        # make it runnable ; it is a temporary condition due
        # to concurrency ; it means that some ancestor space
        # has not yet transferred all required information to
        # the space 
    

    def _distributable(self):
        if self.status not in (Failed, Succeeded, Merged):
            return self._distributable_domains()
        return False
        # in The Book : "the space has one thread that is
        # suspended on a choice point with two or more alternatives.
        # A space canhave at most one choice point; attempting to
        # create another gives an error."

    def _distributable_domains(self):
        for var in self.vars:
            if var.cs_get_dom(self).size() > 1 :
                return True
        return False

    def set_distributor(self, dist):
        self.distributor = dist

    def ask(self):
        # XXX: block on status being not stable for threads
        try:
            self.status_condition.acquire()
            while not self._stable():
                self.status_condition.wait()
            if self._distributable():
                return Alternatives(self.distributor.nb_subdomains())
            return self.status
        finally:
            self.status_condition.release()

    def clone(self):
        spc = ComputationSpace(NoProblem, parent=self)
        for var in spc.vars:
            var.cs_set_dom(spc, var.cs_get_dom(self).copy())
        # check satisfiability of the space
        spc._process()
        if spc.status == Distributable:
            spc.distributor.start()
        return spc

    def inject(self, restricting_problem):
        """add additional stuff into a space"""
        pass

    def commit(self, choice):
        """if self is distributable, causes the Choose call in the
           space to complete and return some_number as a result. This
           may cause the spzce to resume execution.
           some_number must satisfy 1=<I=<N where N is the first arg
           of the Choose call.
        """
        self.bind(self.CHOICE, choice)

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
        self.ask()
        choice = self.CHOICE.get()
        self.CHOICE = self._make_choice_var()
        return choice    

    def _make_choice_var(self):
        ComputationSpace._nb_choices += 1
        return self.var('__choice__'+str(self._nb_choices))

    def make_children(self):
        for dommap in self.distributor.distribute():
            cs = ComputationSpace(lambda cs : True,
                                  parent=self)
            self.children.add(cs)
            for var, dom in dommap.items():
                var.cs_set_dom(cs, dom)

    def solve_all(self):
        """recursively solves the problem
        """
        if self.status == Unprocessed:
            self.process()
            if self.status == Succeeded: return self.root
            if self.status == Failed: raise Failed
            self.make_children()
            results = set() # to be merged/committed ?
            for cs in self.children:
                try:
                    results.add(cs.solve_all())
                except Failed:
                    pass
            for result in results:
                # Q: do we (a) merge our children results right now
                #    or (b) do we pass results up the call chain ?
                # (b) makes sense for a SolveAll kind of method on cs's
                # (a) might be more Oz-ish, maybe allowing some very fancy
                #     stuff with distribution or whatever
                self.do_something_with(result)




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
from problems import dummy_problem
_cs = ComputationSpace(dummy_problem)

#-- global accessor functions
def var(name):
    v = Var(name, _cs)
    _cs.add_unbound(v)
    return v

def set_domain(var, dom):
    return _cs.set_domain(var, dom)

def add_constraint(constraint):
    return _cs.add_constraint(constraint)

def satisfiable(constraint):
    return _cs.satisfiable(constraint)

def get_satisfying_domains(constraint):
    return _cs.get_satisfying_domains(constraint)

def satisfy(constraint):
    return _cs.satisfy(constraint)

def bind(var, val):
    return _cs.bind(var, val)

def unify(var1, var2):
    return _cs.unify(var1, var2)
