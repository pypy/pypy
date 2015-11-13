from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.backend.zarch.runner import CPU_S390_64
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.history import (AbstractFailDescr,
                                            AbstractDescr,
                                            BasicFailDescr, BasicFinalDescr,
                                            JitCellToken, TargetToken,
                                            ConstInt, ConstPtr,
                                            Const, ConstFloat)
from rpython.jit.metainterp.resoperation import InputArgInt, InputArgFloat
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.metainterp.resoperation import ResOperation, rop
import py

class FakeStats(object):
    pass

class TestZARCH(LLtypeBackendTest):
    # for the individual tests see
    # ====> ../../test/runner_test.py

    def get_cpu(self):
        cpu = CPU_S390_64(rtyper=None, stats=FakeStats())
        cpu.setup_once()
        return cpu

    @py.test.mark.parametrize('value,opcode,result',
        [ (30,'i1 = int_mul(i0, 2)',60),
          (30,'i1 = int_floordiv(i0, 2)',15),
          (2**31,'i1 = int_floordiv(i0, 15)',2**31//15),
          (0,'i1 = int_floordiv(i0, 1)', 0),
          (1,'i1 = int_floordiv(i0, 1)', 1),
          (0,'i1 = uint_floordiv(i0, 1)', 0),
          (1,'i1 = uint_floordiv(i0, 1)', 1),
          (30,'i1 = int_mod(i0, 2)', 0),
          (1,'i1 = int_mod(i0, 2)', 1),
          (1,'i1 = int_lshift(i0, 4)', 16),
          (1,'i1 = int_lshift(i0, 0)', 1),
          (4,'i1 = int_rshift(i0, 0)', 4),
          (4,'i1 = int_rshift(i0, 1)', 2),
          (-1,'i1 = int_rshift(i0, 0)', -1),
          (-1,'i1 = int_lshift(i0, 1)', -2),
          (-2**35,'i1 = int_lshift(i0, 1)', (-2**35)*2),
          (2**64-1,'i1 = uint_rshift(i0, 2)', (2**64-1)//4),
          (-1,'i1 = int_neg(i0)', -1),
          (1,'i1 = int_neg(i0)', -1),
          (2**63-1,'i1 = int_neg(i0)', -(2**63-1)),
          (1,'i1 = int_invert(i0)', ~1),
          (15,'i1 = int_invert(i0)', ~15),
          (-1,'i1 = int_invert(i0)', ~(-1)),
          (0,'i1 = int_is_zero(i0)', 1),
          (50,'i1 = int_is_zero(i0)', 0),
          (-1,'i1 = int_is_true(i0)', 1),
          (0,'i1 = int_is_true(i0)', 0),
        ])
    def test_int_arithmetic_and_logic(self, value, opcode, result):
        loop = parse("""
        [i0]
        {opcode}
        finish(i1, descr=faildescr)
        """.format(opcode=opcode),namespace={"faildescr": BasicFinalDescr(1)})
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        deadframe = self.cpu.execute_token(looptoken, value)
        fail = self.cpu.get_latest_descr(deadframe)
        res = self.cpu.get_int_value(deadframe, 0)
        assert res == result
        assert fail.identifier == 1 

    @py.test.mark.parametrize('value,opcode,result,guard',
        [ (-2**63,  'i1 = int_add_ovf(i0, 1)', -2**63, 'guard_no_overflow'),
          (-2**63+1,'i1 = int_add_ovf(i0, 1)', -2**63, 'guard_no_overflow'),
          (-2**63+1,'i1 = int_add_ovf(i0, 1)', -2**63+1, 'guard_overflow'),
        ])
    def test_int_arithmetic_overflow(self, value, opcode, result, guard):
        code = """
        [i0]
        {opcode}
        {guard}() [i0]
        finish(i1, descr=faildescr)
        """.format(opcode=opcode,guard=guard)
        loop = parse(code, namespace={"faildescr": BasicFinalDescr(1)})
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        deadframe = self.cpu.execute_token(looptoken, value)
        fail = self.cpu.get_latest_descr(deadframe)
        res = self.cpu.get_int_value(deadframe, 0)
        assert res == result
        #assert fail.identifier == 1 

    def test_double_evenodd_pair(self):
        # TODO
        pass

    def test_double_evenodd_pair_spill(self):
        # TODO
        pass
