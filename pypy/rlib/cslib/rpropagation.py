"""The code of the constraint propagation algorithms"""
from pypy.rlib.cslib.rconstraint import AbstractConstraint, ConsistencyError

class Repository:
    """Stores variables, domains and constraints
    Propagates domain changes to constraints
    Manages the constraint evaluation queue"""

    def __init__(self, domains, constraints):
        self._variables = domains.keys()   # list of variable names
        self._domains = domains    # maps variable name to domain object
        self._constraints = [] # list of constraint objects
        self._varconst = {}
        for var in self._variables:
            self._varconst[var] = []
        for constr in constraints:
            self.add_constraint( constr )

    def __repr__(self):
        return '<Repository nb_constraints=%d domains=%s>' % \
                               (len(self._constraints), self._domains)

    def add_constraint(self, constraint):
        assert isinstance( constraint, AbstractConstraint )
        if 0: # isinstance(constraint, BasicConstraint):
            # Basic constraints are processed just once
            # because they are straight away entailed
            var = constraint.getVariable()
            constraint.revise({var: self._domains[var]})
        else:
            self._constraints.append(constraint)
            for var in constraint._variables:
                self._varconst[var].append(constraint)
        
    def _remove_constraint(self, constraint):
        self._constraints.remove(constraint)
        for var in constraint._variables:
            try:
                self._varconst[var].remove(constraint)
            except ValueError:
                raise ValueError('Error removing constraint from listener',
                                 var,
                                 self._varconst[var],
                                 constraint)

    def get_domains(self):
        return self._domains

    def distribute(self, distributor):
        """
        create new repository using the distributor and self
        using changed domains
        """
        d1, d2 = distributor.distribute(self._domains)
        return [Repository(d1, self._constraints),
                Repository(d2, self._constraints)]
    
    def propagate(self):
        """Prunes the domains of the variables
        This method calls constraint.narrow() and queues constraints
        that are affected by recent changes in the domains.
        Returns True if a solution was found"""

        _queue = [(constr.estimate_cost(self._domains), constr)
                  for constr in self._constraints ]
        # XXX : _queue.sort()
        _affected_constraints = {}
        while True:
            if not _queue:
                # refill the queue if some constraints have been affected
                _queue = [(constr.estimate_cost(self._domains), constr)
                          for constr in _affected_constraints]
                if not _queue:
                    break
                # XXX _queue.sort()
                _affected_constraints.clear()
            cost, constraint = _queue.pop(0)
            entailed = constraint.revise(self._domains)
            for var in constraint._variables:
                # affected constraints are listeners of
                # affected variables of this constraint
                dom = self._domains[var]
                if not dom._changed: # XXX
                    continue
                for constr in self._varconst[var]:
                    if constr is not constraint:
                        _affected_constraints[constr] = True
                dom._changed = False
            if entailed:
                self._remove_constraint(constraint)
                if constraint in _affected_constraints:
                    del _affected_constraints[constraint]
                
        for domain in self._domains.values():
            if domain.size() != 1:
                return 0
        return 1


    def solve_all(self, distributor):
        solver = Solver(distributor)
        return solver.solve_all(self)


import os

class Solver:
    """Top-level object used to manage the search"""

    def __init__(self, distributor):
        """if no distributer given, will use the default one"""
        self._verb = 0
        self._distributor = distributor
        self.todo = []

    def solve_one(self, repository):
        self.todo = [repository]
        return self.next_sol()

    def solve_all(self, repository):
        self.todo = [repository]
        solutions = []
        while True:
            sol = self.next_sol()
            if sol is not None:
                solutions.append( sol )
                if self._verb:
                    os.write(1, 'found solution : %s\n' % sol)
            else:
                break
        return solutions

    def next_sol(self):
        found_solution = False
        todo = self.todo
        while todo:
            repo = todo.pop()
            try:
                found_solution = repo.propagate()
            except ConsistencyError:
                continue
            if found_solution:
                solution = {}
                for variable, domain in repo.get_domains().items():
                    solution[variable] = domain.get_values()[0]
                return solution
            else:
                for rep in repo.distribute(self._distributor):
                    todo.append( rep )
        return None
    
