
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

    print "ready to find solution ..."
    while sp_stack:
        space = sp_stack.pop()
        print ' '*len(sp_stack), "ask [depth = %s]" % len(sp_stack)
        status = space.ask()
        if status == 1:
            print ' '*len(sp_stack), "solution !"
            yield space.merge()
        elif status > 1:
            print ' '*len(sp_stack), "%s branches ..." % status
            for i in xrange(status):
                clone = space.clone()
                clone.commit(status-i)
                collect(clone)
        elif status == 0:
            print ' '*len(sp_stack), "dead-end"

solve = lazily_iter_solve_all
