from pypy.translator.simplify import get_graph
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype
from pypy.translator.backendopt import graphanalyze

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("canraise") 
py.log.setconsumer("canraise", ansi_log) 

class RaiseAnalyzer(graphanalyze.GraphAnalyzer):
    def operation_is_true(self, op):
        try:
            return bool(LL_OPERATIONS[op.opname].canraise)
        except KeyError:
            log.WARNING("Unknown operation: %s" % op.opname)
            return True

    def analyze_exceptblock(self, block, seen=None):
        return True

    # backward compatible interface
    def can_raise(self, op, seen=None):
        return self.analyze(op, seen)
