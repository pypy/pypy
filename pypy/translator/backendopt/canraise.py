from pypy.translator.simplify import get_graph
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype
from pypy.translator.backendopt import graphanalyze
from pypy.translator.simplify import get_funcobj

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("canraise") 
py.log.setconsumer("canraise", ansi_log) 

class RaiseAnalyzer(graphanalyze.BoolGraphAnalyzer):
    def analyze_simple_operation(self, op, graphinfo):
        try:
            return bool(LL_OPERATIONS[op.opname].canraise)
        except KeyError:
            log.WARNING("Unknown operation: %s" % op.opname)
            return True

    def analyze_external_call(self, op, seen=None):
        fnobj = get_funcobj(op.args[0].value)
        return getattr(fnobj, 'canraise', True)

    def analyze_external_method(self, op, TYPE, meth):
        assert op.opname == 'oosend'
        return getattr(meth, '_can_raise', True)

    def analyze_exceptblock(self, block, seen=None):
        return True

    # backward compatible interface
    def can_raise(self, op, seen=None):
        return self.analyze(op, seen)
