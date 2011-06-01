from pypy.jit.metainterp.history import (AbstractFailDescr,
                                         AbstractDescr,
                                         BasicFailDescr,
                                         BoxInt, Box, BoxPtr,
                                         LoopToken,
                                         ConstInt, ConstPtr,
                                         BoxObj, Const,
                                         ConstObj, BoxFloat, ConstFloat)
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref
from pypy.jit.tool.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rffi, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.llinterp import LLException
from pypy.jit.codewriter import heaptracker, longlong
from pypy.rlib.rarithmetic import intmask
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.test.runner_test import Runner

def boxfloat(x):
    return BoxFloat(longlong.getfloatstorage(x))

def constfloat(x):
    return ConstFloat(longlong.getfloatstorage(x))

class FakeStats(object):
    pass
class TestCallingConv(Runner):
    type_system = 'lltype'
    Ptr = lltype.Ptr
    FuncType = lltype.FuncType

    def __init__(self):
        self.cpu = getcpuclass()(rtyper=None, stats=FakeStats())
        self.cpu.setup_once()

    def _prepare_args(self, args, floats, ints):
        local_floats = list(floats)
        local_ints = list(ints)
        expected_result = 0.0
        for i in range(len(args)):
            x = args[i]
            if x[0] == 'f':
                x = local_floats.pop()
                t = longlong.getfloatstorage(x)
                self.cpu.set_future_value_float(i, t)
            else:
                x = local_ints.pop()
                self.cpu.set_future_value_int(i, x)
            expected_result += x
        return expected_result

    @classmethod
    def get_funcbox(cls, cpu, func_ptr):
        addr = llmemory.cast_ptr_to_adr(func_ptr)
        return ConstInt(heaptracker.adr2int(addr))

    def test_call_aligned_with_spilled_values(self):
            from pypy.rlib.libffi import types
            cpu = self.cpu
            if not cpu.supports_floats:
                py.test.skip('requires floats')


            def func(*args):
                return float(sum(args))

            F = lltype.Float
            I = lltype.Signed
            floats = [0.7, 5.8, 0.1, 0.3, 0.9, -2.34, -3.45, -4.56]
            ints = [7, 11, 23, 13, -42, 1111, 95, 1]
            for case in range(256):
                local_floats = list(floats)
                local_ints = list(ints)
                args = []
                spills = []
                funcargs = []
                float_count = 0
                int_count = 0
                for i in range(8):
                    if case & (1<<i):
                        args.append('f%d' % float_count)
                        spills.append('force_spill(f%d)' % float_count)
                        float_count += 1
                        funcargs.append(F)
                    else:
                        args.append('i%d' % int_count)
                        spills.append('force_spill(i%d)' % int_count)
                        int_count += 1
                        funcargs.append(I)

                arguments = ', '.join(args)
                spill_ops = '\n'.join(spills)

                FUNC = self.FuncType(funcargs, F)
                FPTR = self.Ptr(FUNC)
                func_ptr = llhelper(FPTR, func)
                calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
                funcbox = self.get_funcbox(cpu, func_ptr)

                ops = '[%s]\n' % arguments
                ops += '%s\n' % spill_ops
                ops += 'f99 = call(ConstClass(func_ptr), %s, descr=calldescr)\n' % arguments
                ops += 'finish(f99, %s)\n' % arguments

                loop = parse(ops, namespace=locals())
                looptoken = LoopToken()
                done_number = self.cpu.get_fail_descr_number(loop.operations[-1].getdescr())
                self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
                expected_result = self._prepare_args(args, floats, ints)

                res = self.cpu.execute_token(looptoken)
                x = longlong.getrealfloat(cpu.get_latest_value_float(0))
                assert abs(x - expected_result) < 0.0001

    def test_call_aligned_with_imm_values(self):
            from pypy.rlib.libffi import types
            cpu = self.cpu
            if not cpu.supports_floats:
                py.test.skip('requires floats')


            def func(*args):
                return float(sum(args))

            F = lltype.Float
            I = lltype.Signed
            floats = [0.7, 5.8, 0.1, 0.3, 0.9, -2.34, -3.45, -4.56]
            ints = [7, 11, 23, 13, -42, 1111, 95, 1]
            for case in range(256):
                result = 0.0
                args = []
                argslist = []
                local_floats = list(floats)
                local_ints = list(ints)
                for i in range(8):
                    if case & (1<<i):
                        args.append(F)
                        arg = local_floats.pop()
                        result += arg
                        argslist.append(constfloat(arg))
                    else:
                        args.append(I)
                        arg = local_ints.pop()
                        result += arg
                        argslist.append(ConstInt(arg))
                FUNC = self.FuncType(args, F)
                FPTR = self.Ptr(FUNC)
                func_ptr = llhelper(FPTR, func)
                calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
                funcbox = self.get_funcbox(cpu, func_ptr)

                res = self.execute_operation(rop.CALL,
                                             [funcbox] + argslist,
                                             'float', descr=calldescr)
                assert abs(res.getfloat() - result) < 0.0001

    def test_call_aligned_with_args_on_the_stack(self):
            from pypy.rlib.libffi import types
            cpu = self.cpu
            if not cpu.supports_floats:
                py.test.skip('requires floats')


            def func(*args):
                return float(sum(args))

            F = lltype.Float
            I = lltype.Signed
            floats = [0.7, 5.8, 0.1, 0.3, 0.9, -2.34, -3.45, -4.56]
            ints = [7, 11, 23, 13, -42, 1111, 95, 1]
            for case in range(256):
                result = 0.0
                args = []
                argslist = []
                local_floats = list(floats)
                local_ints = list(ints)
                for i in range(8):
                    if case & (1<<i):
                        args.append(F)
                        arg = local_floats.pop()
                        result += arg
                        argslist.append(boxfloat(arg))
                    else:
                        args.append(I)
                        arg = local_ints.pop()
                        result += arg
                        argslist.append(BoxInt(arg))
                FUNC = self.FuncType(args, F)
                FPTR = self.Ptr(FUNC)
                func_ptr = llhelper(FPTR, func)
                calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
                funcbox = self.get_funcbox(cpu, func_ptr)

                res = self.execute_operation(rop.CALL,
                                             [funcbox] + argslist,
                                             'float', descr=calldescr)
                assert abs(res.getfloat() - result) < 0.0001

    def test_call_alignment_call_assembler(self):
        from pypy.rlib.libffi import types
        cpu = self.cpu
        if not cpu.supports_floats:
            py.test.skip('requires floats')

        fdescr3 = BasicFailDescr(3)
        fdescr4 = BasicFailDescr(4)

        def assembler_helper(failindex, virtualizable):
            assert 0, 'should not be called, but was with failindex (%d)' % failindex
            return 13

        FUNCPTR = lltype.Ptr(lltype.FuncType([lltype.Signed, llmemory.GCREF],
                                             lltype.Signed))
        class FakeJitDriverSD:
            index_of_virtualizable = -1
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)

        floats = [0.7, 5.8, 0.1, 0.3, 0.9, -2.34, -3.45, -4.56]
        ints = [7, 11, 23, 42, -42, 1111, 95, 1]

        for case in range(256):
            float_count = 0
            int_count = 0
            args = []
            called_ops = ''
            total_index = -1
            for i in range(8):
                if case & (1<<i):
                    args.append('f%d' % float_count)
                else:
                    args.append('i%d' % int_count)
                    called_ops += 'f%d = cast_int_to_float(i%d)\n' % (
                        float_count, int_count)
                    int_count += 1
                if total_index == -1:
                    total_index = float_count
                    float_count += 1
                else:
                    called_ops += 'f%d = float_add(f%d, f%d)\n' % (
                        float_count + 1, total_index, float_count)
                    total_index = float_count + 1
                    float_count += 2
            arguments = ', '.join(args)
            called_ops = '[%s]\n' % arguments + called_ops
            called_ops += 'finish(f%d, descr=fdescr3)\n' % total_index
            # compile called loop
            called_loop = parse(called_ops, namespace=locals())
            called_looptoken = LoopToken()
            called_looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
            done_number = self.cpu.get_fail_descr_number(called_loop.operations[-1].getdescr())
            self.cpu.compile_loop(called_loop.inputargs, called_loop.operations, called_looptoken)

            expected_result = self._prepare_args(args, floats, ints)
            res = cpu.execute_token(called_looptoken)
            assert res.identifier == 3
            t = longlong.getrealfloat(cpu.get_latest_value_float(0))
            assert abs(t - expected_result) < 0.0001

            ARGS = []
            RES = lltype.Float
            for x in args:
                if x[0] == 'f':
                    ARGS.append(lltype.Float)
                else:
                    ARGS.append(lltype.Signed)
            FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
                lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES)
            ops = '''
            [%s]
            f99 = call_assembler(%s, descr=called_looptoken)
            guard_not_forced()[]
            finish(f99, descr=fdescr4)
            ''' % (arguments, arguments)
            loop = parse(ops, namespace=locals())
            # we want to take the fast path
            self.cpu.done_with_this_frame_float_v = done_number
            try:
                othertoken = LoopToken()
                self.cpu.compile_loop(loop.inputargs, loop.operations, othertoken)

                # prepare call to called_loop
                self._prepare_args(args, floats, ints)
                res = cpu.execute_token(othertoken)
                x = longlong.getrealfloat(cpu.get_latest_value_float(0))
                assert res.identifier == 4
                assert abs(x - expected_result) < 0.0001
            finally:
                del self.cpu.done_with_this_frame_float_v

