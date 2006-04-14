from pypy.translator.simplify import get_graph
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype
from pypy.translator.backendopt import graphanalyze

class RaiseAnalyzer(graphanalyze.GraphAnalyzer):
    def operation_is_true(self, op):
        try:
            return bool(LL_OPERATIONS[op.opname].canraise)
        except KeyError:
            return True

    def analyze_exceptblock(self, block, seen=None):
        return True

    # backward compatible interface
    def can_raise(self, op, seen=None):
        return self.analyze(op, seen)
