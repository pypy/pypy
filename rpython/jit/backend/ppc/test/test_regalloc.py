from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem import rclass, rstr
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.objectmodel import instantiate
from rpython.jit.backend.ppc.locations import (imm, RegisterLocation,
                                               ImmLocation, StackLocation)
from rpython.jit.backend.ppc.register import *
from rpython.jit.backend.ppc.codebuilder import hi, lo
from rpython.jit.backend.ppc.ppc_assembler import AssemblerPPC
from rpython.jit.backend.ppc.arch import WORD
from rpython.jit.backend.ppc.locations import get_spp_offset
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.codewriter import longlong
from rpython.jit.metainterp.history import BasicFailDescr, \
     JitCellToken, TargetToken
from rpython.jit.tool.oparser import parse

class MockBuilder(object):
    
    def __init__(self):
        self.reset()

    def __getattr__(self, name):
        instr = MockInstruction(name)
        self.instrs.append(instr)
        return instr

    def str_instrs(self):
        return [str(inst) for inst in self.instrs]

    def reset(self):
        self.instrs = []

class MockInstruction(object):

    def __init__(self, name, *args):
        self.name = name
        self.args = args

    def __call__(self, *args):
        self.args = args

    def __eq__(self, other):
        assert isinstance(other, MockInstruction)
        return self.name == other.name and self.args == other.args

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "%s %r" % (self.name, self.args)
    

MI = MockInstruction

class TestMocks(object):
    
    def setup_method(self, method):
        self.builder = MockBuilder()

    def test_cmp_instruction(self):
        assert MI("a", 1, 2) == MI("a", 1, 2)
        assert not MI("a", 1, 2) == MI("b", 1, 2)
        assert not MI("a", 1, 2) == MI("a", 2, 2)
        assert not MI("a", 1) == MI("a", 1, 2)
        assert not MI("a", 1, 2) == MI("a")
        assert MI("a") == MI("a")

    def test_basic(self):
        exp_instrs = [MI("mr", 3, 5), 
                      MI("foobar"),
                      MI("li", 3, 2),
                      MI("stw", 3, 5, 100)]

        self.builder.mr(3, 5)
        self.builder.foobar()
        self.builder.li(3, 2)
        self.builder.stw(3, 5, 100)
       
        assert self.builder.instrs == exp_instrs
        
        self.builder.blub()
        assert self.builder.instr != exp_instrs

class TestRegallocMov(object):
    
    def setup_method(self, method):
        self.builder = MockBuilder()
        self.asm = instantiate(AssemblerPPC)
        self.asm.mc = self.builder

    def test_immediate_to_reg(self):
        self.asm.regalloc_mov(imm(5), r10)
        big = 2 << 28
        self.asm.regalloc_mov(imm(big), r0)

        exp_instr = [MI("load_imm", r10, 5), 
                     MI("load_imm", r0, big)]
        assert self.asm.mc.instrs == exp_instr

    def test_immediate_to_mem(self):
        self.asm.regalloc_mov(imm(5), stack(6))
        big = 2 << 28
        self.asm.regalloc_mov(imm(big), stack(7))

        exp_instr = [MI("alloc_scratch_reg"),
                     MI("load_imm", r0, 5),
                     MI("store", r0.value, SPP.value, get_spp_offset(6)),
                     MI("free_scratch_reg"),

                     MI("alloc_scratch_reg"),
                     MI("load_imm", r0, big),
                     MI("store", r0.value, SPP.value, get_spp_offset(7)),
                     MI("free_scratch_reg")]
        assert self.asm.mc.instrs == exp_instr

    def test_mem_to_reg(self):
        self.asm.regalloc_mov(stack(5), reg(10))
        self.asm.regalloc_mov(stack(0), reg(0))
        exp_instrs = [MI("load", r10.value, SPP.value, -(5 * WORD + WORD)),
                      MI("load", r0.value, SPP.value, -(WORD))]
        assert self.asm.mc.instrs == exp_instrs

    def test_mem_to_mem(self):
        self.asm.regalloc_mov(stack(5), stack(6))
        exp_instrs = [
                      MI("alloc_scratch_reg"),
                      MI("load", r0.value, SPP.value, get_spp_offset(5)),
                      MI("store", r0.value, SPP.value, get_spp_offset(6)),
                      MI("free_scratch_reg")]
        assert self.asm.mc.instrs == exp_instrs

    def test_reg_to_reg(self):
        self.asm.regalloc_mov(reg(0), reg(1))
        self.asm.regalloc_mov(reg(5), reg(10))
        exp_instrs = [MI("mr", r1.value, r0.value),
                      MI("mr", r10.value, r5.value)]
        assert self.asm.mc.instrs == exp_instrs

    def test_reg_to_mem(self):
        self.asm.regalloc_mov(reg(5), stack(10))
        self.asm.regalloc_mov(reg(0), stack(2))
        exp_instrs = [MI("store", r5.value, SPP.value, -(10 * WORD + WORD)),
                      MI("store", r0.value, SPP.value, -(2 * WORD + WORD))]
        assert self.asm.mc.instrs == exp_instrs

def reg(i):
    return RegisterLocation(i)

def stack(i):
    return StackLocation(i)

CPU = getcpuclass()
class BaseTestRegalloc(object):
    cpu = CPU(None, None)
    cpu.setup_once()

    def raising_func(i):
        if i:
            raise LLException(zero_division_error,
                              zero_division_value)
    FPTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Void))
    raising_fptr = llhelper(FPTR, raising_func)

    def f(a):
        return 23

    FPTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
    f_fptr = llhelper(FPTR, f)
    f_calldescr = cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT,
                                                    EffectInfo.MOST_GENERAL)

    zero_division_tp, zero_division_value = cpu.get_zero_division_error()
    zd_addr = cpu.cast_int_to_adr(zero_division_tp)
    zero_division_error = llmemory.cast_adr_to_ptr(zd_addr,
                                            lltype.Ptr(rclass.OBJECT_VTABLE))
    raising_calldescr = cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT,
                                                    EffectInfo.MOST_GENERAL)

    targettoken = TargetToken()
    targettoken2 = TargetToken()
    fdescr1 = BasicFailDescr(1)
    fdescr2 = BasicFailDescr(2)
    fdescr3 = BasicFailDescr(3)

    def setup_method(self, meth):
        self.targettoken._arm_loop_code = 0
        self.targettoken2._arm_loop_code = 0

    def f1(x):
        return x + 1

    def f2(x, y):
        return x * y

    def f10(*args):
        assert len(args) == 10
        return sum(args)

    F1PTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
    F2PTR = lltype.Ptr(lltype.FuncType([lltype.Signed] * 2, lltype.Signed))
    F10PTR = lltype.Ptr(lltype.FuncType([lltype.Signed] * 10, lltype.Signed))
    f1ptr = llhelper(F1PTR, f1)
    f2ptr = llhelper(F2PTR, f2)
    f10ptr = llhelper(F10PTR, f10)

    f1_calldescr = cpu.calldescrof(F1PTR.TO, F1PTR.TO.ARGS, F1PTR.TO.RESULT,
                                                    EffectInfo.MOST_GENERAL)
    f2_calldescr = cpu.calldescrof(F2PTR.TO, F2PTR.TO.ARGS, F2PTR.TO.RESULT,
                                                    EffectInfo.MOST_GENERAL)
    f10_calldescr = cpu.calldescrof(F10PTR.TO, F10PTR.TO.ARGS,
                                    F10PTR.TO.RESULT, EffectInfo.MOST_GENERAL)

    namespace = locals().copy()
    type_system = 'lltype'

    def parse(self, s, boxkinds=None):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system,
                     boxkinds=boxkinds)

    def interpret(self, ops, args, run=True):
        loop = self.parse(ops)
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        arguments = []
        for arg in args:
            if isinstance(arg, int):
                arguments.append(arg)
            elif isinstance(arg, float):
                arg = longlong.getfloatstorage(arg)
                arguments.append(arg)
            else:
                assert isinstance(lltype.typeOf(arg), lltype.Ptr)
                llgcref = lltype.cast_opaque_ptr(llmemory.GCREF, arg)
                arguments.append(llgcref)
        loop._jitcelltoken = looptoken
        if run:
            self.cpu.execute_token(looptoken, *arguments)
        return loop

    def prepare_loop(self, ops):
        loop = self.parse(ops)
        regalloc = Regalloc(assembler=self.cpu.assembler,
        frame_manager=ARMFrameManager())
        regalloc.prepare_loop(loop.inputargs, loop.operations)
        return regalloc

    def getint(self, index):
        return self.cpu.get_latest_value_int(index)

    def getfloat(self, index):
        v = self.cpu.get_latest_value_float(index)
        return longlong.getrealfloat(v)

    def getints(self, end):
        return [self.cpu.get_latest_value_int(index) for
                index in range(0, end)]

    def getfloats(self, end):
        return [self.getfloat(index) for
                index in range(0, end)]

    def getptr(self, index, T):
        gcref = self.cpu.get_latest_value_ref(index)
        return lltype.cast_opaque_ptr(T, gcref)

    def attach_bridge(self, ops, loop, guard_op_index, **kwds):
        guard_op = loop.operations[guard_op_index]
        assert guard_op.is_guard()
        bridge = self.parse(ops, **kwds)
        assert ([box.type for box in bridge.inputargs] ==
                [box.type for box in guard_op.getfailargs()])
        faildescr = guard_op.getdescr()
        self.cpu.compile_bridge(faildescr, bridge.inputargs, bridge.operations,
                                loop._jitcelltoken)
        return bridge

    def run(self, loop, *args):
        return self.cpu.execute_token(loop._jitcelltoken, *args)


