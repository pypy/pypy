## The Constraint-based computation model
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

from unification import Store, var
from constraint import ConsistencyFailure
from threading import Thread, Condition

class Unprocessed:
    pass

class Working:
    pass

class Failed(Exception):
    pass

class Merged:
    """Its constraint store has been added to a parent.
       Any further operation operation on the space is
       an error.
    """
    pass

class Succeeded:
    """It contains no choice points but a solution to
       the logic program.
    """
    pass


class ComputationSpace(object):

    def __init__(self, program, parent=None):
        if parent is None:
            self.store = Store()
            self.root = self.store.var('root')
            self.store.bind(self.root, program(self))
        else:
            self.store = parent.store
            self.root = parent.root
        self.program = program
        self.parent = parent
        # status
        self.status = Unprocessed
        self.status_condition = Condition()
        # run ...
        self._process()

    def _process(self):
        try:
            self.store.satisfy_all()
        except ConsistencyFailure:
            self.status = Failed
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
            return self.distributor.findSmallestDomain() > 1
        # in The Book : "the space has one thread that is
        # suspended on a choice point with two or more alternatives.
        # A space canhave at most one choice point; attempting to
        # create another gives an error."

    def set_distributor(self, dist):
        self.distributor = dist

    def ask(self):
        # XXX: block on status being not stable for threads
        try:
            self.status_condition.acquire()
            while not self._stable():
                self.status_condition.wait()
            if self._distributable():
                return self.distributor.nb_subdomains()
            return self.status
        finally:
            self.status_condition.release()


    def make_children(self):
        for dommap in self.distributor.distribute():
            cs = ComputationSpace(lambda cs : True,
                                  parent=self)
            self.children.add(cs)
            for var, dom in dommap.items():
                var.cs_set_dom(cs, dom)


    def commit(self, some_number):
        """if self is distributable, causes the Choose call in the
           space ot complete and return some_number as a result. This
           may cause the spzce to resume execution.
           some_number must satisfy 1=<I=<N where N is the first arg
           of the Choose call.
        """
        pass

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
            

        
