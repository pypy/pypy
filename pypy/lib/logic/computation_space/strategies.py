import computationspace as csp

class StrategyDistributionMismatch(Exception):
    pass

def dfs_one(problem):
    """depth-first single-solution search
       assumes the space default distributor is
       dichotomic"""

    def do_dfs(space):
        print "do_dfs"
        status = space.ask()
        if status == csp.Failed:
            return None
        elif status == csp.Succeeded:
            return space
        elif status == csp.Alternative(2):
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



#-- solve_all, switchable direction

class Depth: pass
class Breadth: pass

def solve_all(problem, direction=Depth):

    solutions = []
    sp_stack = []
    sp_stack.append(csp.ComputationSpace(problem))

    if direction == Depth:
        def collect(space):
            sp_stack.append(space)
    else:
        def collect(space):
            sp_stack.insert(0, space)

    while len(sp_stack):
        space = sp_stack.pop()
        print ' '*len(sp_stack), "ask ..."
        status = space.ask()
        if status == csp.Succeeded:
            print ' '*len(sp_stack), "solution !"
            solutions.append(space)
        elif status == csp.Alternative(2):
            print ' '*len(sp_stack), "branches ..."
            sp1 = space.clone()
            sp1.commit(1)
            collect(sp1)
            sp2 = space.clone()
            sp2.commit(2)
            collect(sp2)

    return [sp.merge() for sp in solutions]

#-- pythonic lazy solve_all

def lazily_solve_all(space, direction=Depth):

    sp_stack = []
    sp_stack.append(space)

    if direction == Depth:
        def collect(space):
            sp_stack.append(space)
    else:
        def collect(space):
            sp_stack.insert(0, space)

    while len(sp_stack):
        space = sp_stack.pop()
        print ' '*len(sp_stack), "ask ..."
        status = space.ask()
        if status == csp.Succeeded:
            print ' '*len(sp_stack), "solution !"
            yield space.merge()
        elif status == csp.Alternative(2):
            print ' '*len(sp_stack), "branches ..."
            sp1 = space.clone()
            sp1.commit(1)
            collect(sp1)
            sp2 = space.clone()
            sp2.commit(2)
            collect(sp2)
