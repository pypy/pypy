from pypy.translator.simplify import get_graph
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype

class ExceptionInfo(object):
    def __init__(self, translator, can_raise, cannot_raise=None):
        self.can_raise = can_raise
        self.cannot_raise = cannot_raise
        self.translator = translator

    def exception_match(self, etype):
        pass

class RaiseAnalyzer(object):
    def __init__(self, translator):
        self.translator = translator
        self.call_can_raise = {}

    def can_raise(self, op, seen=None):
        if op.opname == "direct_call":
            graph = get_graph(op.args[0], self.translator)
            print "graph", graph
            if graph is None:
                return True
            return self.direct_call_can_raise(graph, seen)
        elif op.opname == "indirect_call":
            return self.indirect_call_can_raise(op.args[-1].value, seen)
        else:
            return bool(LL_OPERATIONS[op.opname].canraise)

    def direct_call_can_raise(self, graph, seen=None):
        if graph in self.call_can_raise:
            return self.call_can_raise[graph]
        if seen is None:
            seen = {}
        if graph in seen:
            self.call_can_raise[graph] = False
            return False
        else:
            seen[graph] = True
        for block in graph.iterblocks():
            if block is graph.exceptblock:
                return True # the except block is reached
            for op in block.operations:
                if self.can_raise(op, seen):
                    self.call_can_raise[graph] = True
                    return True
        self.call_can_raise[graph] = False
        return False

    def indirect_call_can_raise(self, graphs, seen=None):
        if graphs is None:
            return True
        for graph in graphs:
            if self.direct_call_can_raise(graph, seen):
                return True
        return False
