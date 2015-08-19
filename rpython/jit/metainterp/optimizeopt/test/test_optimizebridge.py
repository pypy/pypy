
from rpython.jit.metainterp.optimizeopt.test.test_util import BaseTest,\
     LLtypeMixin, convert_old_style_to_targets
from rpython.jit.metainterp import compile
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.metainterp.history import TargetToken

class TestOptimizeBridge(BaseTest, LLtypeMixin):
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"

    def optimize(self, ops, bridge_ops, expected, inline_short_preamble=True):
        loop = self.parse(ops, postprocess=self.postprocess)
        info = self.unroll_and_optimize(loop, None)
        jitcell_token = compile.make_jitcell_token(None)
        mid_label_descr = TargetToken(jitcell_token)
        start_label_descr = TargetToken(jitcell_token)
        jitcell_token.target_tokens = [mid_label_descr, start_label_descr]
        loop.operations[0].setdescr(mid_label_descr)
        loop.operations[-1].setdescr(mid_label_descr)
        info.preamble.operations[0].setdescr(start_label_descr)
        guards = [op for op in loop.operations if op.is_guard()]
        assert len(guards) == 1, "more than one guard in the loop"
        bridge = self.parse(bridge_ops, postprocess=self.postprocess)
        start_label = ResOperation(rop.LABEL, bridge.inputargs)
        bridge.operations[-1].setdescr(jitcell_token)
        data = compile.BridgeCompileData(start_label, bridge.operations,
                                         enable_opts=self.enable_opts,
                            inline_short_preamble=inline_short_preamble)
        bridge_info, ops = self._do_optimize_loop(data)
        loop.check_consistency(check_descr=False)
        info.preamble.check_consistency(check_descr=False)
        bridge.operations = ([ResOperation(rop.LABEL, bridge_info.inputargs)] +
                             ops)
        bridge.inputargs = bridge_info.inputargs
        bridge.check_consistency(check_descr=False)
        expected = self.parse(expected, postprocess=self.postprocess)
        self.assert_equal(bridge, convert_old_style_to_targets(expected,
                                                               jump=True))
    
    def test_simple(self):
        loop = """
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_is_true(i1)
        guard_true(i2) [i1, i2]
        jump(i1)
        """
        bridge = """
        [i0, i1]
        jump(i1)
        """
        expected = """
        [i0, i1]
        jump(i1)
        """
        self.optimize(loop, bridge, expected)
