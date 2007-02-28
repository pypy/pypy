
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

    #print "ready to find solution ..."
    while sp_stack:
        space = sp_stack.pop()
        #print ' '*len(sp_stack), "ask [depth = %s]" % len(sp_stack)
        status = space.ask()
        if status == 1:
            #print ' '*len(sp_stack), "solution !"
            yield space.merge()
        elif status > 1:
            #print ' '*len(sp_stack), "%s branches ..." % status
            for i in xrange(status):
                clone = space.clone()
                clone.commit(status-i)
                collect(clone)
        elif status == 0:
            pass
            #print ' '*len(sp_stack), "dead-end"

solve = lazily_iter_solve_all


#-- dfs with recomputations


def recompute(space, branches_list):
    # branches_list contains the recomputation path,
    # bottom-up
    if branches_list == None:
        return space.clone()
    else:
        head, tail = branches_list
        C = recompute(space, tail)
        C.ask()
        C.commit(head)
        return C

def dfre(S, R, branches_list, distance, max_dist, solutions):
    status = S.ask()
    if status == 0:
        return
    elif status == 1:
        solutions.append(S.merge())
        return
    else:
        assert status == 2
        if distance == max_dist:
            C = S.clone()
            S.commit(1)
            dfre(S, C, (1,None), 1, max_dist, solutions)
            C.commit(2)
            dfre(C, C, None, max_dist, max_dist, solutions)
        else:
            S.commit(1)
            dfre(S, R, (1, branches_list), distance+1, max_dist, solutions)
            C = recompute(R, branches_list)
            C.ask()
            C.commit(2)
            dfre(C, R, (2, branches_list), distance+1, max_dist, solutions)

def solve_recomputing(space, recomputation_distance=5):
    solutions = []
    dfre(space, space, None, recomputation_distance, recomputation_distance, solutions)
    return solutions

