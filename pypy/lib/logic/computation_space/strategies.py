import computationspace as csp

class StrategyDistributionMismatch(Exception):
    pass

def dfs_one_solution(problem):
    """depth-first single-solution search
       assumes the space default distributor is
       dichotomic"""

    def do_dfs(space):
        status = space.ask()
        if status == csp.Failed:
            return None
        elif status == csp.Succeeded:
            return [space]
        elif status == csp.Alternatives(2):
            new_space = space.clone()
            space.commit(1)
            outcome = do_dfs(space)
            if outcome is None:
                new_space.commit(2)
                return do_dfs(new_space)
            else:
                return outcome
        else:
            raise StrategyDistributionMismatch()
                                               
    
    space = csp.ComputationSpace(problem)
    outcome = do_dfs(space)
    if outcome == None: return None
    space.merge()
    return space


