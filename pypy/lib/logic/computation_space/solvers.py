import computationspace as csp

class StrategyDistributionMismatch(Exception):
    pass

#--- this set of solvers assumes a dichotomic distributor

Alternatives = 2

def rec_solve_one(problem):
    """depth-first single-solution search
       assumes the space default distributor is
       dichotomic"""

    def do_dfs(space):
        print "do_dfs_one"
        status = space.ask()
        if status == csp.Failed:
            return None
        elif status == csp.Succeeded:
            return space
        elif status == Alternatives:
            new_space = space.clone()
            space.commit(1)
            outcome = do_dfs(space)
            if outcome is None:
                new_space.ask()
                new_space.commit(2)
                outcome = do_dfs(new_space)
            return outcome
        else:
            raise StrategyDistributionMismatch()
                                               
    space = csp.ComputationSpace(problem)
    solved_space = do_dfs(space)
    if solved_space == None: return None
    return solved_space.merge()

#-- solve_all, switchable direction (takes problem)

from collections import deque

class Depth: pass
class Breadth: pass

def iter_solve_all(problem, direction=Depth):

    solutions = []
    sp_stack = deque([])
    sp_stack.append(csp.ComputationSpace(problem))

    if direction == Depth:
        def collect(space):
            sp_stack.append(space)
    else:
        def collect(space):
            sp_stack.appendleft(space)

    while len(sp_stack):
        print "depth is ", len(sp_stack)
        space = sp_stack.pop()
        print ' '*len(sp_stack), "ask ..."
        status = space.ask()
        if status == csp.Succeeded:
            print ' '*len(sp_stack), "solution !"
            solutions.append(space)
        elif status == Alternatives:
            print ' '*len(sp_stack), "branches ..."
            sp1 = space.clone()
            sp1.commit(1)
            collect(sp1)
            sp2 = space.clone()
            sp2.commit(2)
            collect(sp2)

    return [sp.merge() for sp in solutions]

#-- pythonic lazy solve_all (takes space)

def lazily_iter_solve_all(space, direction=Depth):

    sp_stack = deque([])
    sp_stack.append(space)

    if direction == Depth:
        def collect(space):
            sp_stack.append(space)
    else:
        def collect(space):
            sp_stack.appendleft(space)

    while len(sp_stack):
        space = sp_stack.pop()
        print ' '*len(sp_stack), "ask ..."
        status = space.ask()
        if status == csp.Succeeded:
            print ' '*len(sp_stack), "solution !"
            yield space.merge()
        elif status == Alternatives:
            print ' '*len(sp_stack), "branches ..."
            sp1 = space.clone()
            sp1.commit(1)
            collect(sp1)
            sp2 = space.clone()
            sp2.commit(2)
            collect(sp2)
