
""" More direct tests for unrolling
"""

from rpython.jit.metainterp.optimizeopt.test.test_util import BaseTest,\
     LLtypeMixin
from rpython.jit.metainterp.history import (TreeLoop, ConstInt,
                                            JitCellToken, TargetToken)
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.compile import LoopCompileData
from rpython.jit.metainterp.optimizeopt.virtualstate import \
     NotVirtualStateInfo, LEVEL_CONSTANT, LEVEL_UNKNOWN
from rpython.jit.codewriter import heaptracker

class FakeOptimizer(object):
    optearlyforce = None
     
class BaseTestUnroll(BaseTest, LLtypeMixin):
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"
    
    def optimize(self, ops):
        loop = self.parse(ops, postprocess=self.postprocess)
        self.add_guard_future_condition(loop)
        operations =  loop.operations
        jumpop = operations[-1]
        assert jumpop.getopnum() == rop.JUMP
        inputargs = loop.inputargs

        jump_args = jumpop.getarglist()[:]
        operations = operations[:-1]

        preamble = TreeLoop('preamble')
        preamble.inputargs = inputargs

        token = JitCellToken()
        start_label = ResOperation(rop.LABEL, inputargs, descr=TargetToken(token))
        stop_label = ResOperation(rop.LABEL, jump_args, descr=token)
        compile_data = LoopCompileData(start_label, stop_label, operations)
        start_state, newops = self._do_optimize_loop(compile_data)
        preamble.operations = newops
        return start_state, loop, preamble

class TestUnroll(BaseTestUnroll):
    def test_simple(self):
        loop = """
        [i0]
        i1 = int_add(i0, 1)
        guard_value(i1, 1) []
        jump(i1)
        """
        es, loop, preamble = self.optimize(loop)
        vs = es.virtual_state
        assert isinstance(vs.state[0], NotVirtualStateInfo)
        # the virtual state is constant, so we don't need to have it in
        # inputargs
        assert vs.make_inputargs([1], FakeOptimizer()) == []
        assert vs.state[0].level == LEVEL_CONSTANT
        # we have exported values for i1, which happens to be an inputarg
        assert es.inputarg_mapping[0][1].getint() == 1
        assert isinstance(es.inputarg_mapping[0][1], ConstInt)
        assert es.short_boxes == {}

    def test_not_constant(self):
        loop = """
        [i0]
        i1 = int_add(i0, 1)
        jump(i0)
        """
        es, loop, preamble = self.optimize(loop)
        vs = es.virtual_state
        assert isinstance(vs.state[0], NotVirtualStateInfo)
        assert vs.state[0].level == LEVEL_UNKNOWN
        op = preamble.operations[0]
        assert es.short_boxes == {op: op}

    def test_guard_class(self):
        loop = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        es, loop, preamble = self.optimize(loop)
        p0 = loop.inputargs[0]
        assert (heaptracker.adr2int(self.node_vtable_adr) ==
                es.exported_infos[p0]._known_class.getint())


