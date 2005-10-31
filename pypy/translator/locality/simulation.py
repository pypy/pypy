"""

Simulation of function calls
----------------------------

The purpose of this module is to simulate function calls
in the call-graph of a program, to gather information
about frequencies of transitions between functions.

The following SimNode/SimGraph classes show an example of the
simulation performed. They can be subclassed to connect them
to client structures like flowgraphs.

- SimGraph.run was used to get an obviously correct reference implementation.

- SimGraph.sim_all simulates the calls of the run method. The results are
  exactly the same, although the computation time ir orders of magnitudes
  smaller, and the SimGraph.simulate method is able to handle recursions
  and function call probabilities which are fractions.
"""


class SimNode:
    def __init__(self, sim, func):
        self.sim = sim
        self.func = func
        self.name = self._get_name(func)
        self.callees = []
        self._callers = None # computed
        self.calls = 0

    def __repr__(self):
        return '(%s)' % self.name

    def __cmp__(self, other):
        if isinstance(other, self.__class__):
            return cmp(self.name, other.name)
        return cmp(id(self), id(other))

    def __hash__(self):
        return id(self)

    def _get_name(self, func):
        # to be overridden
        return func.__name__

    def _find_callee_names(self):
        # to be overridden
        return self.func.func_code.co_names

    def call(self):
        self.calls += 1
        for i in range(self.sim.repetitions_per_call):
            for func in self.callees:
                self.sim.record_transition(self, func)
                func.call()

    def clear(self):
        self.calls = 0

    def simulate_call(self, weight=1):
        self.calls += weight

    # calls and returns are symmetric. We provide a callers
    # interface that is computed on demand.

    def _get_callers(self):
        if not self.sim._callers_computed:
            self.sim._compute_callers()
        return self.callers
    callers = property(_get_callers)

    def get_relations(self):
        # get callees and callers with frequency, ordered
        # by decreasing frequency and then by name.
        ret = []
        for node in self.callees:
            freq = self.sim.transitions[ (self, node) ]
            ret.append( (-freq, node) )
        for node in self.callers:
            freq = self.sim.transitions[ (node, self) ]
            ret.append( (-freq, node) )
        # if there is nothing, link it to itself
        if not ret:
            ret.append( (-1, self) )
        ret.sort()
        freqs, nodes = zip(*ret)
        return nodes, [-freq for freq in freqs]


class SimGraph:
    def __init__(self, funcnodes, nodefactory=SimNode, clientdata=None):
        self.nodes = []
        self.transitions = {}
        self.pending = {}
        self.clientdata = clientdata

        name2node = {}
        for func in funcnodes:
            node = nodefactory(self, func)
            name2node[node.name] = node
            self.nodes.append(node)
        self._names_width = self._find_names_width()
        for node in self.nodes:
            for name in node._find_callee_names():
                callee = name2node[name]
                node.callees.append(callee)
                self.transitions[ (node, callee) ] = 0
        self._callers_computed = False

    def _find_names_width(self):
        n = 0
        for node in self.nodes:
            n = max(n, len(node.name))
        return n

    def record_transition(self, caller, callee, weight=1):
        self.transitions[ (caller, callee) ] += weight

    def run(self, reps=1, root=0):
        self._callers_computed = False
        self.repetitions_per_call = reps
        root = self.nodes[root]
        root.call()

    def run_all(self, reps=1):
        for root in range(len(self.nodes)):
            self.run(reps, root)

    def clear(self):
        for key in self.transitions:
            self.transitions[key] = 0
        for node in self.nodes:
            node.clear()
        self.pending.clear()

    def display(self):
        d = {'w': max(self._names_width, 6) }
        print '%%%(w)ds %%%(w)gs  repetition' % d % ('caller', 'callee')
        for caller, callee, reps in self.get_state():
            print '%%%(w)ds %%%(w)gs %%6g' % d % (caller, callee, reps)
        print '%%%(w)gs  calls' % d % 'node'
        for node in self.nodes:
            print '%%%(w)gs %%6g' % d % (node.name, node.calls)

    def get_state(self):
        lst = []
        for (caller, callee), reps in self.transitions.items():
            lst.append( (caller.name, callee.name, reps) )
        lst.sort()
        return lst

    def simulate(self, call_prob=1, root=None):
        # simulating runs by not actually calling, but shooting
        # the transitions in a weighted manner.
        # this allows us to handle recursions as well.
        # first, stimulate nodes if no transitions are pending
        self._callers_computed = False
        if not self.pending:
            if root is not None:
                startnodes = [self.nodes[root]]
            else:
                startnodes = self.nodes
            for node in startnodes:
                self.pending[node] = 1
        # perform a single step of simulated calls.
        pending = {}
        for caller, ntrans in self.pending.items():
            caller.simulate_call(ntrans)
            for callee in caller.callees:
                self.record_transition(caller, callee, ntrans * call_prob)
                pending[callee] = pending.get(callee, 0) + ntrans * call_prob
        self.pending = pending

    def sim_all(self, call_prob=1, maxrun=None, root=None):
        # simulate and stop after maxrun loops
        self.simulate(call_prob, root)
        i = 0
        while self.pending:
            self.simulate(call_prob)
            i += 1
            if maxrun and i >= maxrun:
                break

    def _compute_callers(self):
        nodes = {}
        for node in self.nodes:
            nodes[node] = node
            node.callers = []
        returns = [ (callee, caller)
                    for caller, callee in self.transitions.keys()]
        returns.sort()
        for callee, caller in returns:
            nodes[callee].callers.append(caller)

# sample functions for proof of correctness

def test(debug=False):

    def a(): b(); c(); d()
    def b(): c(); d()
    def c(): pass
    def d(): c(); e()
    def e(): c()
    sim = SimGraph([a, b, c, d, e])
    if debug:
        globals().update(locals())

    sim.clear()
    for prob in 1, 3, 2:
        sim.clear()
        sim.run_all(prob)
        state1 = sim.get_state()
        sim.clear()
        sim.sim_all(prob)
        state2 = sim.get_state()
        assert state1 == state2
    return sim

if __name__ == '__main__':
    test()
