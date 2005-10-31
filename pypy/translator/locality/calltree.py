"""

CallTree

An approach to do static call analysis in the PyPy backend
to produce a somewhat locality-of-reference optimized
ordering of the function objects in the generated source.

In extent to that, it is planned to produce a non-optimized
binary from instrumented source code, run some sample
applications and optimize according to transition statistics.
This step will only be done if the first approach shows any
improvement.

Sketch of the algorithm:
------------------------
In a first pass, we inspect all function nodes for direct_call
opcodes and record the callees, if they are constants.
(Variables will later be tried to find out by re-using the
information in the translator).

We then run a simulation of calls.
See pypy/translator/locality/simulation.py.

After that, a poly-dimensional model is computed and morphed
into a one-dimensional ordering.
See pypy/translator/locality/projection.py.
"""

from pypy.objspace.flow.model import Variable, Constant
from pypy.translator.locality.support import log
from pypy.translator.locality.simulation import SimNode, SimGraph
from pypy.translator.locality.projection import SpaceNode, SpaceGraph


class FlowSimNode(SimNode):
    def _get_name(self, func):
        return func.name

    def _find_callee_names(self):
        calls = self.sim.clientdata[self.func]
        return [func.name for func in calls]


class CallTree:
    def __init__(self, funcnodes, database):
        self.nodes = funcnodes
        self.database = database
        self.graphs2nodes = self._build_graph2nodes()
        self.calls = {}
        for node in self.nodes:
            self.calls[node] = self.find_callees(node)

    def _build_graph2nodes(self):
        dic = {}
        for node in self.nodes:
            dic[node.obj.graph] = node
        return dic

    def find_callees(self, node):
        graph = node.obj.graph
        res = []
        if node.obj._callable in self.database.externalfuncs:
            s = "skipped external function %s" % node.obj._callable.__name__
            log.calltree.findCallees(s)
            return res
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'direct_call':
                    fnarg = op.args[0]
                    if isinstance(fnarg, Constant):
                        fnptr = fnarg.value
                        fn = fnptr._obj
                        graph = fn.graph
                        try:
                            callednode = self.graphs2nodes[graph]
                        except KeyError:
                            s = "No node found for graph %s" % graph.name
                            log.calltree.findCallees(s)
                            continue
                        else:
                            res.append(callednode)
                    else:
                        s = "Node %s calls Variable %s" % (node.name, fnarg)
                        log.calltree.findCallees(s)
        return res

    def simulate(self):
        log.simulate('building SimGraph for simulation...')
        sim = SimGraph(self.nodes, FlowSimNode, self.calls)
        log.simulate('simulating...')
        sim.sim_all(1.9, 50)
        self.statgraph = sim

    def optimize(self):
        log.topology('building SpaceGraph for topological sort...')
        sg = SpaceGraph(self.statgraph)
        steps = 500
        try:
            for i in range(steps):
                for k in range(10):
                    sg.do_correction()
                sg.normalize()
                s = "step %d of %d lonelyness = %g" % (i+1, steps, sg.lonelyness())
                log.topology(s)
        except KeyboardInterrupt:
            log.topology("aborted after %d steps" % (i+1))
        self.topology = sg
        log.topology("done.")

    def ordered_funcnodes(self):
        nodes = self.topology.order()
        ret = [node.func for node in nodes]
        return ret
