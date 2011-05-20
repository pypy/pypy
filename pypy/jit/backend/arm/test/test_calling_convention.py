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

