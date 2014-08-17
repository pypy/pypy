import py

from rpython.rtyper.lltypesystem.lloperation import LL_OPERATIONS
from rpython.tool.ansi_print import ansi_log
from rpython.translator.backendopt import graphanalyze

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
        fnobj = op.args[0].value._obj
        return getattr(fnobj, 'canraise', True)

    def analyze_exceptblock(self, block, seen=None):
        return True

    # backward compatible interface
    def can_raise(self, op, seen=None):
        return self.analyze(op, seen)
