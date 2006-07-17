
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


#-- dfs with recomputations

class Chain(object):
    def __init__(self, space=None, parent=None, distance=1):
        self.space = space
        self.parent = parent
        self.distance = distance
        self.child = None
        self.last_branch = None
    def set_branches(self, branches):
        self.branches = range(branches)
    def collect_space(self, space):
        self.child = Chain(space, parent=self,
                           distance=self.distance + 1)
        return self.child
    def clone_time(self):
        return self.distance % recomputation_distance

def dfs_with_recomputations(space, recomputation_distance=1):
    assert recomputation_distance > 0

    node = Chain(space)

    def get_space():
        # XXX: write me
        pass
        
    while node:
        space = get_space()
        status = space.ask()
        if status == 1:
            yield space.merge()
        elif status > 1:
            if node.clone_time():
                clone = space.clone()
                if node.child is None:
                    node.set_branges(status)
                branch = node.branches.pop()
                node.last_branch = branch # recomputation info
                node = node.collect(clone)
                clone.commit(branch)
            else:
                #find previous clone_time node
                cur = node.parent
                while not cur.clone_time():
                    cur = cur.parent
                # take a clone of the local space,
                # replay all the branches
                clone = cur.space.clone()
                while cur.child:
                    clone.commit(cur.last_branch)
                    cur = cur.child
                # now, do the new computation
                # XXX: factor me out
                assert cur is node
                branch = node.branches.pop()
                node.last_branch = branch
                node = node.collect(None)
                clone.commit(branch)
