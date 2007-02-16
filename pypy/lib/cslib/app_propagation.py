"""The code of the constraint propagation algorithms"""

import operator
#from time import strftime

class ConsistencyFailure(Exception):
    """The repository is not in a consistent state"""
    pass

class Repository(object):
    """Stores variables, domains and constraints
    Propagates domain changes to constraints
    Manages the constraint evaluation queue"""
    
    def __init__(self, variables, domains, constraints = None):
        # encode unicode
        for i, var in enumerate(variables):
            if type(var) == type(u''):
                variables[i] = var.encode()
                
        self._variables = variables   # list of variable names
        self._domains = domains    # maps variable name to domain object
        self._constraints = [] # list of constraint objects
#        self._queue = []       # queue of constraints waiting to be processed
        self._variableListeners = {}
        for var in self._variables:
            self._variableListeners[var] = []
            assert self._domains.has_key(var)
        for constr in constraints or ():
            self.addConstraint(constr)

    def __repr__(self):
        return '<Repository nb_constraints=%d domains=%s>' % \
                               (len(self._constraints), self._domains)

    def addConstraint(self, constraint):
        if isinstance(constraint, BasicConstraint):
            # Basic constraints are processed just once
            # because they are straight away entailed
            var = constraint.getVariable()
            constraint.narrow({var: self._domains[var]})
        else:
            self._constraints.append(constraint)
            for var in constraint.affectedVariables():
                self._variableListeners[var].append(constraint)
        
    def _removeConstraint(self, constraint):
        self._constraints.remove(constraint)
        for var in constraint.affectedVariables():
            try:
                self._variableListeners[var].remove(constraint)
            except ValueError:
                raise ValueError('Error removing constraint from listener',
                                 var,
                                 self._variableListeners[var],
                                 constraint)

    def getDomains(self):
        return self._domains

    def distribute(self, distributor, verbose=0):
        """Create new repository using the distributor and self """
        for domains in distributor.distribute(self._domains, verbose):
            yield Repository(self._variables, domains, self._constraints) 
    
    def revise(self, verbose=0):
        """Prunes the domains of the variables
        This method calls constraint.narrow() and queues constraints
        that are affected by recent changes in the domains.
        Returns True if a solution was found"""
        if verbose:
            print '** Consistency **'

        _queue = [ (constr.estimateCost(self._domains),
                           constr) for constr in self._constraints ]
        _queue.sort()
        _affected_constraints = {}
        while True:
            if not _queue:
                # refill the queue if some constraints have been affected
                _queue = [(constr.estimateCost(self._domains),
                           constr) for constr in _affected_constraints]
                if not _queue:
                    break
                _queue.sort()
                _affected_constraints.clear()
            if verbose > 2:
                print 'Queue', _queue
            cost, constraint = _queue.pop(0)
            if verbose > 1:
                print 'Trying to entail constraint',
                print constraint, '[cost:%d]' % cost
            entailed = constraint.narrow(self._domains)
            for var in constraint.affectedVariables():
                # affected constraints are listeners of
                # affected variables of this constraint
                dom = self._domains[var]
                if not dom.has_changed():
                    continue
                if verbose > 1 :
                    print ' -> New domain for variable', var, 'is', dom
                for constr in self._variableListeners[var]:
                    if constr is not constraint:
                        _affected_constraints[constr] = True
                dom.clear_change()
            if entailed:
                if verbose:
                    print "--> Entailed constraint", constraint
                self._removeConstraint(constraint)
                if constraint in _affected_constraints:
                    del _affected_constraints[constraint]
                
        for domain in self._domains.itervalues():
            if domain.size() != 1:
                return 0
        return 1

class Solver(object):
    """Top-level object used to manage the search"""

    def __init__(self, distributor=None):
        """if no distributer given, will use the default one"""
        if distributor is None:
            from distributors import DefaultDistributor
            distributor = DefaultDistributor()
        self._distributor = distributor
        self.verbose = 1
        self.max_depth = 0

    def solve_one(self, repository, verbose=0):
        """Generates only one solution"""
        self.verbose = verbose
        self.max_depth = 0
        try:
            return  self._solve(repository).next()
        except StopIteration:
            return
        
    def solve_best(self, repository, cost_func, verbose=0):
        """Generates solution with an improving cost"""
        self.verbose = verbose
        self.max_depth = 0
        best_cost = None
        for solution in self._solve(repository):
            cost = cost_func(**solution)
            if best_cost is None or cost <= best_cost:
                best_cost = cost
                yield solution, cost            
        
    def solve_all(self, repository, verbose=0):
        """Generates all solutions"""
        self.verbose = verbose
        self.max_depth = 0
        for solution in self._solve(repository):
            yield solution

    def solve(self, repository, verbose=0):
        """return list of all solutions"""
        self.max_depth = 0
        solutions = []
        for solution in self.solve_all(repository, verbose):
            solutions.append(solution)
        return solutions
        
    def _solve(self, repository, recursion_level=0):
        """main generator"""
        solve = self._solve
        verbose = self.verbose
        if recursion_level > self.max_depth:
            self.max_depth = recursion_level
        if verbose:
            print '*** [%d] Solve called with repository' % recursion_level,
            print repository
        try:
            foundSolution = repository.revise(verbose)
        except ConsistencyFailure, exc:
            if verbose:
                print exc
            pass
        else:
            if foundSolution: 
                solution = {}
                for variable, domain in repository.getDomains().items():
                    solution[variable] = domain.get_values()[0]
                if verbose:
                    print '### Found Solution', solution
                    print '-'*80
                yield solution
            else:
                for repo in repository.distribute(self._distributor,
                                                  verbose):
                    for solution in solve(repo, recursion_level+1):
                        if solution is not None:
                            yield solution
                            
        if recursion_level == 0 and self.verbose:
            print 'Finished search'
            print 'Maximum recursion depth = ', self.max_depth

        




class BasicConstraint(object):
    """A BasicConstraint, which is never queued by the Repository
    A BasicConstraint affects only one variable, and will be entailed
    on the first call to narrow()"""

    def __init__(self, variable, reference, operator):
        """variables is a list of variables on which
        the constraint is applied"""
        self._variable = variable
        self._reference = reference
        self._operator = operator

    def __repr__(self):
        return '<%s %s %s>'% (self.__class__, self._variable, self._reference)

    def isVariableRelevant(self, variable):
        return variable == self._variable

    def estimateCost(self, domains):
        return 0 # get in the first place in the queue
    
    def affectedVariables(self):
        return [self._variable]
    
    def getVariable(self):
        return self._variable
        
    def narrow(self, domains):
        domain = domains[self._variable]
        operator = self._operator
        ref = self._reference
        try:
            for val in domain.getValues() :
                if not operator(val, ref) :
                    domain.removeValue(val)
        except ConsistencyFailure:
            raise ConsistencyFailure('inconsistency while applying %s' % \
                                     repr(self))
        return 1


class AbstractDomain(object):
    """Implements the functionnality related to the changed flag.
    Can be used as a starting point for concrete domains"""

    def __init__(self):
        self.__changed = 0

    def resetFlags(self):
        self.__changed = 0
    
    def hasChanged(self):
        return self.__changed

    def _valueRemoved(self):
        """The implementation of removeValue should call this method"""
        self.__changed = 1
        if self.size() == 0:
            raise ConsistencyFailure()
    
class AbstractConstraint(object):
    
    def __init__(self, variables):
        """variables is a list of variables which appear in the formula"""
        self._variables = variables

    def affectedVariables(self):
        """ Return a list of all variables affected by this constraint """
        return self._variables

    def isVariableRelevant(self, variable):
        return variable in self._variables

    def estimateCost(self, domains):
        """Return an estimate of the cost of the narrowing of the constraint"""
        return reduce(operator.mul,
                      [domains[var].size() for var in self._variables])

    
