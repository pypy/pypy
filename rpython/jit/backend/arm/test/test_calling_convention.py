from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.backend.test.calling_convention_test import CallingConvTests, parse
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.codewriter.effectinfo import EffectInfo

from rpython.jit.backend.arm.codebuilder import ARMv7Builder
from rpython.jit.backend.arm import registers as r
from rpython.jit.backend.arm.test.support import skip_unless_run_slow_tests
skip_unless_run_slow_tests()

class TestARMCallingConvention(CallingConvTests):
    # ../../test/calling_convention_test.py

    def make_function_returning_stack_pointer(self):
        mc = ARMv7Builder()
	mc.MOV_rr(r.r0.value, r.sp.value)
	mc.MOV_rr(r.pc.value, r.lr.value)
        return mc.materialize(self.cpu.asmmemmgr, [])

    def get_alignment_requirements(self):
        return 8

    def test_call_argument_spilling(self):
        # bug when we have a value in r0, that is overwritten by an argument
        # and needed after the call, so that the register gets spilled after it
        # was overwritten with the argument to the call
        def func(a):
            return a + 16

        I = lltype.Signed
        FUNC = self.FuncType([I], I)
        FPTR = self.Ptr(FUNC)
        func_ptr = llhelper(FPTR, func)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT, EffectInfo.MOST_GENERAL)
        funcbox = self.get_funcbox(self.cpu, func_ptr)

        args = ', '.join(['i%d' % i for i in range(11)])
        ops = """
        [%s]
        i99 = call(ConstClass(func_ptr), 22, descr=calldescr)
        force_spill(i0)
        force_spill(i1)
        force_spill(i2)
        force_spill(i3)
        force_spill(i4)
        force_spill(i5)
        force_spill(i6)
        force_spill(i7)
        force_spill(i8)
        force_spill(i9)
        force_spill(i10)
        guard_true(i0) [%s, i99]
        finish()""" % (args, args)
        loop = parse(ops, namespace=locals())
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        args = [x for x in range(11)]
        deadframe = self.cpu.execute_token(looptoken, *args)
        for x in range(11):
            assert self.cpu.get_int_value(deadframe, x) == x
        assert self.cpu.get_int_value(deadframe, 11) == 38
