import py, sys, random, os, struct, operator
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

CPU = getcpuclass()

class TestFrameSize(object):
    cpu = CPU(None, None)
    cpu.setup_once()

    looptoken = None
    
    def f1(x):
        return x+1

    F1PTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
    f1ptr = llhelper(F1PTR, f1)
    f1_calldescr = cpu.calldescrof(F1PTR.TO, F1PTR.TO.ARGS, F1PTR.TO.RESULT)
    namespace = locals().copy()
    type_system = 'lltype'

    def parse(self, s, boxkinds=None):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system,
                     boxkinds=boxkinds)

    def interpret(self, ops, args, run=True):
        loop = self.parse(ops)
        self.cpu.compile_loop(loop.inputargs, loop.operations, loop.token)
        for i, arg in enumerate(args):
            if isinstance(arg, int):
                self.cpu.set_future_value_int(i, arg)
            elif isinstance(arg, float):
                self.cpu.set_future_value_float(i, arg)
            else:
                assert isinstance(lltype.typeOf(arg), lltype.Ptr)
                llgcref = lltype.cast_opaque_ptr(llmemory.GCREF, arg)
                self.cpu.set_future_value_ref(i, llgcref)
        if run:
            self.cpu.execute_token(loop.token)
        return loop

    def getint(self, index):
        return self.cpu.get_latest_value_int(index)

    def getfloat(self, index):
        return self.cpu.get_latest_value_float(index)

    def getints(self, end):
        return [self.cpu.get_latest_value_int(index) for
                index in range(0, end)]

    def getfloats(self, end):
        return [self.cpu.get_latest_value_float(index) for
                index in range(0, end)]

    def getptr(self, index, T):
        gcref = self.cpu.get_latest_value_ref(index)
        return lltype.cast_opaque_ptr(T, gcref)

    

    def test_call_loop_from_loop(self): 

        large_frame_loop = """ 
        [i0, i1, i2, i3, i4, i5, i6, i7, i8, i9, i10, i11, i12, i13, i14]
        i15 = call(ConstClass(f1ptr), i0, descr=f1_calldescr)
        finish(i0, i1, i2, i3, i4, i5, i6, i7, i8, i9, i10, i11, i12, i13, i14, i15)
        """ 
        large = self.interpret(large_frame_loop, range(15), run=False)
        self.namespace['looptoken'] = large.token
        assert self.namespace['looptoken']._arm_func_addr != 0
        small_frame_loop = """
        [i0]
        i1 = int_add(i0, 1)
        jump(i1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, descr=looptoken)
        """

        self.interpret(small_frame_loop, [110])
        expected = [111, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 112]
        assert self.getints(16) == expected

