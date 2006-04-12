
class StrategyDistributionMismatch(Exception):
    pass


from collections import deque

class Depth: pass
class Breadth: pass

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
        if status == 1:
            print ' '*len(sp_stack), "solution !"
            yield space.merge()
        elif status > 1:
            print ' '*len(sp_stack), "branches ..."
            sp1 = space.clone()
            sp1.commit(1)
            collect(sp1)
            sp2 = space.clone()
            sp2.commit(2)
            collect(sp2)

solve = lazily_iter_solve_all
