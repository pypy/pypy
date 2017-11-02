from rpython.rtyper.lltypesystem.lloperation import LL_OPERATIONS
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper import rclass
from rpython.tool.ansi_print import AnsiLogger
from rpython.translator.backendopt import graphanalyze
from rpython.flowspace import model as flowmodel

log = AnsiLogger("canraise")


class RaiseAnalyzer(graphanalyze.BoolGraphAnalyzer):
    ignore_exact_class = None

    def __init__(self, translator):
        graphanalyze.BoolGraphAnalyzer.__init__(self, translator)
        ed = translator.rtyper.exceptiondata
        self.ll_assert_error = ed.get_standard_ll_exc_instance_by_class(
            AssertionError)
        self.ll_not_impl_error = ed.get_standard_ll_exc_instance_by_class(
            NotImplementedError)

    def do_ignore_memory_error(self):
        self.ignore_exact_class = MemoryError

    def analyze_simple_operation(self, op, graphinfo):
        try:
            canraise = LL_OPERATIONS[op.opname].canraise
            return bool(canraise) and canraise != (self.ignore_exact_class,)
        except KeyError:
            log.WARNING("Unknown operation: %s" % op.opname)
            return True

    def analyze_external_call(self, fnobj, seen=None):
        return getattr(fnobj, 'canraise', True)

    analyze_exceptblock = None    # don't call this

    def analyze_exceptblock_in_graph(self, graph, block, seen=None):
        def producer(block, v):
            for op in block.operations:
                if op.result is v:
                    return op
            assert False

        if self.ignore_exact_class is not None:
            from rpython.translator.backendopt.ssa import DataFlowFamilyBuilder
            dff = DataFlowFamilyBuilder(graph)
            variable_families = dff.get_variable_families()
            v_exc_instance = variable_families.find_rep(block.inputargs[1])
            for link1 in graph.iterlinks():
                v = link1.last_exc_value
                if v is not None:
                    if variable_families.find_rep(v) is v_exc_instance:
                        # this is a case of re-raise the exception caught;
                        # it doesn't count.  We'll see the place that really
                        # raises the exception in the first place.
                        return False
        # find all the blocks leading to the raise block
        blocks = []
        for candidate in graph.iterblocks():
            if len(candidate.exits) != 1:
                continue
            if candidate.exits[0].target is block:
                blocks.append(candidate)
        ignored = 0
        import pdb
        pdb.set_trace()
        for preblock in blocks:
            exc_val = preblock.exits[0].args[1]
            if isinstance(exc_val, flowmodel.Constant):
                exc = exc_val.value
            else:
                # find the producer
                op = producer(preblock, exc_val)
                if op.opname == 'cast_pointer':
                    exc_val = op.args[0]
                    op = producer(preblock, exc_val)
                if op.opname != 'same_as':
                    # something strange, return True
                    return True
                exc = op.args[0].value
            p = lltype.cast_pointer(rclass.OBJECTPTR, exc)
            if p == self.ll_assert_error or p == self.ll_not_impl_error:
                ignored += 1
        return ignored < len(blocks)

    # backward compatible interface
    def can_raise(self, op, seen=None):
        return self.analyze(op, seen)
