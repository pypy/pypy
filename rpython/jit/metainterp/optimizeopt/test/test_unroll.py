
""" More direct tests for unrolling
"""

from rpython.jit.metainterp.optimizeopt.test.test_util import BaseTest,\
     LLtypeMixin, FakeMetaInterpStaticData
from rpython.jit.metainterp.history import (TreeLoop, AbstractDescr, ConstInt,
                                            JitCellToken, TargetToken)
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.optimizeopt.virtualstate import \
     NotVirtualStateInfo, LEVEL_CONSTANT, LEVEL_UNKNOWN

class FakeOptimizer(object):
    optearlyforce = None
     
class TestUnroll(BaseTest, LLtypeMixin):
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"
    
    def optimize(self, ops):
        loop = self.parse(ops, postprocess=self.postprocess)
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
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
        preamble.operations = [start_label] + operations + [stop_label]
        start_state = self._do_optimize_loop(preamble, None,
                                             export_state=True)
        vs = preamble.operations[-1].getdescr().virtual_state
        return start_state, vs, loop

    def test_simple(self):
        loop = """
        [i0]
        i1 = int_add(i0, 1)
        guard_value(i1, 1) []
        jump(i1)
        """
        es, vs, loop = self.optimize(loop)
        assert isinstance(vs.state[0], NotVirtualStateInfo)
        # the virtual state is constant, so we don't need to have it in
        # inputargs
        assert vs.make_inputargs([1], FakeOptimizer()) == []
        assert vs.state[0].level == LEVEL_CONSTANT
        # we have exported values for i1, which happens to be an inputarg
        assert es.inputarg_mapping[0][1].getint() == 1
        assert isinstance(es.inputarg_mapping[0][1], ConstInt)

    def test_not_constant(self):
        loop = """
        [i0]
        i1 = int_add(i0, 1)
        jump(i0)
        """
        es, vs, loop = self.optimize(loop)
        assert isinstance(vs.state[0], NotVirtualStateInfo)
        assert vs.state[0].level == LEVEL_UNKNOWN
