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

class CallTree:
    def __init__(self, funcnodes):
        self.nodes = funcnodes
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
                            print "No node found for graph %s" % graph.name
                            continue
                        else:
                            res.append(callednode)
                    else:
                        print "Node %s calls Variable %s" % (node, fnarg)
        return res
