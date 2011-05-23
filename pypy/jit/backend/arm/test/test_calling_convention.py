import py, sys, random, os, struct, operator, itertools
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

# XXX add a test that tests the direct call assembler thing
# XXX add a test that generates combinations of calls

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

    @classmethod
    def get_funcbox(cls, cpu, func_ptr):
        addr = llmemory.cast_ptr_to_adr(func_ptr)
        return ConstInt(heaptracker.adr2int(addr))

    def test_call_aligned_with_args_on_the_stack(self):
            from pypy.rlib.libffi import types
            cpu = self.cpu
            if not cpu.supports_floats:
                py.test.skip('requires floats')


            def func(*args):
                return sum(args)

            F = lltype.Float
            I = lltype.Signed
            base_args = [F, F]
            floats = [0.7, 5.8, 0.1, 0.3, 0.9]
            ints = [7, 11, 23]
            result = sum(floats + ints)
            for p in itertools.permutations([I, I, I, F, F, F]):
                args = base_args + list(p)
                local_floats = list(floats)
                local_ints = list(ints)
                FUNC = self.FuncType(args, F)
                FPTR = self.Ptr(FUNC)
                func_ptr = llhelper(FPTR, func)
                calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
                funcbox = self.get_funcbox(cpu, func_ptr)
                argslist = []
                for x in args:
                    if x is F:
                        argslist.append(boxfloat(local_floats.pop()))
                    else:
                        argslist.append(BoxInt(local_ints.pop()))

                res = self.execute_operation(rop.CALL,
                                             [funcbox] + argslist,
                                             'float', descr=calldescr)
                assert abs(res.getfloat() - result) < 0.0001

    def test_call_alignment_register_args(self):
            from pypy.rlib.libffi import types
            cpu = self.cpu
            if not cpu.supports_floats:
                py.test.skip('requires floats')


            def func(*args):
                return sum(args)

            F = lltype.Float
            I = lltype.Signed
            floats = [0.7, 5.8]
            ints = [7, 11]
            result = sum(floats + ints)
            for args in itertools.permutations([I, I, F, F]):
                local_floats = list(floats)
                local_ints = list(ints)
                FUNC = self.FuncType(args, F)
                FPTR = self.Ptr(FUNC)
                func_ptr = llhelper(FPTR, func)
                calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
                funcbox = self.get_funcbox(cpu, func_ptr)
                argslist = []
                for x in args:
                    if x is F:
                        argslist.append(boxfloat(local_floats.pop()))
                    else:
                        argslist.append(BoxInt(local_ints.pop()))

                res = self.execute_operation(rop.CALL,
                                             [funcbox] + argslist,
                                             'float', descr=calldescr)
                assert abs(res.getfloat() - result) < 0.0001


    def test_call_alignment_call_assembler(self):
        from pypy.rlib.libffi import types
        cpu = self.cpu
        if not cpu.supports_floats:
            py.test.skip('requires floats')

        fdescr1 = BasicFailDescr(1)
        fdescr2 = BasicFailDescr(2)
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

        arglist = ['f0', 'f1', 'f2', 'i0', 'f3']
        floats = [0.7, 5.8, 0.1, 0.3]
        ints = [7, 11, 23, 42]
        def _prepare_args(args):
            local_floats = list(floats)
            local_ints = list(ints)
            for i in range(len(args)):
                x = args[i]
                if x[0] == 'f':
                    t = longlong.getfloatstorage(local_floats.pop())
                    cpu.set_future_value_float(i, t)
                else:
                    cpu.set_future_value_int(i, (local_ints.pop()))

        for args in itertools.permutations(arglist):
            args += ('i1', 'i2', 'i3')
            arguments = ', '.join(args)
            called_ops = '''
            [%s]
            i4 = int_add(i0, i1)
            i5 = int_add(i4, i2)
            i6 = int_add(i5, i3)
            guard_value(i6, 83, descr=fdescr1) [i4, i5, i6]
            f4 = float_add(f0, f1)
            f5 = float_add(f4, f2)
            f6 = float_add(f5, f3)
            i7 = float_lt(f6, 6.99)
            guard_true(i7, descr=fdescr2) [f4, f5, f6]
            finish(i6, f6, descr=fdescr3)''' % arguments
            # compile called loop
            called_loop = parse(called_ops, namespace=locals())
            called_looptoken = LoopToken()
            called_looptoken.outermost_jitdriver_sd = FakeJitDriverSD()
            done_number = self.cpu.get_fail_descr_number(called_loop.operations[-1].getdescr())
            self.cpu.compile_loop(called_loop.inputargs, called_loop.operations, called_looptoken)

            _prepare_args(args)
            res = cpu.execute_token(called_looptoken)
            assert res.identifier == 3
            assert cpu.get_latest_value_int(0) == 83
            t = longlong.getrealfloat(cpu.get_latest_value_float(1))
            assert abs(t - 6.9) < 0.0001

            ARGS = []
            RES = lltype.Signed
            for x in args:
                if x[0] == 'f':
                    ARGS.append(lltype.Float)
                else:
                    ARGS.append(lltype.Signed)
            FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
                lltype.Ptr(lltype.FuncType(ARGS, RES)), ARGS, RES)
            ops = '''
            [%s]
            i10 = call_assembler(%s, descr=called_looptoken)
            guard_not_forced()[]
            finish(i10, descr=fdescr4)
            ''' % (arguments, arguments)
            loop = parse(ops, namespace=locals())
            # we want to take the fast path
            self.cpu.done_with_this_frame_int_v = done_number
            try:
                othertoken = LoopToken()
                self.cpu.compile_loop(loop.inputargs, loop.operations, othertoken)

                # prepare call to called_loop
                _prepare_args(args)
                res = cpu.execute_token(othertoken)
                x = cpu.get_latest_value_int(0)
                assert res.identifier == 4
                assert x == 83
            finally:
                del self.cpu.done_with_this_frame_int_v
