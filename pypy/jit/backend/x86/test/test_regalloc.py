
""" Tests for register allocation for common constructs
"""

import py
from pypy.jit.metainterp.history import BoxInt, ConstInt,\
     BoxPtr, ConstPtr, LoopToken, BasicFailDescr
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.backend.llsupport.descr import GcCache
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.x86.regalloc import RegAlloc, X86RegisterManager,\
     is_comparison_or_ovf_op
from pypy.jit.backend.x86.arch import IS_X86_32, IS_X86_64
from pypy.jit.tool.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import rclass, rstr
from pypy.jit.codewriter import longlong
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.backend.x86.rx86 import *

def test_is_comparison_or_ovf_op():
    assert not is_comparison_or_ovf_op(rop.INT_ADD)
    assert is_comparison_or_ovf_op(rop.INT_ADD_OVF)
    assert is_comparison_or_ovf_op(rop.INT_EQ)

CPU = getcpuclass()
class MockGcDescr(GcCache):
    def get_funcptr_for_new(self):
        return 123
    get_funcptr_for_newarray = get_funcptr_for_new
    get_funcptr_for_newstr = get_funcptr_for_new
    get_funcptr_for_newunicode = get_funcptr_for_new
 
    def rewrite_assembler(self, cpu, operations):
        pass

class MockAssembler(object):
    gcrefs = None
    _float_constants = None

    def __init__(self, cpu=None, gc_ll_descr=None):
        self.movs = []
        self.performs = []
        self.lea = []
        if cpu is None:
            cpu = CPU(None, None)
            cpu.setup_once()
        self.cpu = cpu
        if gc_ll_descr is None:
            gc_ll_descr = MockGcDescr(False)
        self.cpu.gc_ll_descr = gc_ll_descr

    def dump(self, *args):
        pass

    def regalloc_mov(self, from_loc, to_loc):
        self.movs.append((from_loc, to_loc))

    def regalloc_perform(self, op, arglocs, resloc):
        self.performs.append((op, arglocs, resloc))

    def regalloc_perform_discard(self, op, arglocs):
        self.performs.append((op, arglocs))

    def load_effective_addr(self, *args):
        self.lea.append(args)

def fill_regs(regalloc, cls=BoxInt):
    allboxes = []
    for reg in X86RegisterManager.all_regs:
        box = cls()
        allboxes.append(box)
        regalloc.rm.try_allocate_reg()
    return allboxes
    
class RegAllocForTests(RegAlloc):
    position = 0
    def _compute_next_usage(self, v, _):
        return -1

class BaseTestRegalloc(object):
    cpu = CPU(None, None)
    cpu.setup_once()

    def raising_func(i):
        if i:
            raise LLException(zero_division_error,
                              zero_division_value)
    FPTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Void))
    raising_fptr = llhelper(FPTR, raising_func)
    zero_division_tp, zero_division_value = cpu.get_zero_division_error()
    zd_addr = cpu.cast_int_to_adr(zero_division_tp)
    zero_division_error = llmemory.cast_adr_to_ptr(zd_addr,
                                            lltype.Ptr(rclass.OBJECT_VTABLE))
    raising_calldescr = cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT,
                                        EffectInfo.MOST_GENERAL)

    fdescr1 = BasicFailDescr(1)
    fdescr2 = BasicFailDescr(2)
    fdescr3 = BasicFailDescr(3)

    def f1(x):
        return x+1

    def f2(x, y):
        return x*y

    def f10(*args):
        assert len(args) == 10
        return sum(args)

    F1PTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
    F2PTR = lltype.Ptr(lltype.FuncType([lltype.Signed]*2, lltype.Signed))
    F10PTR = lltype.Ptr(lltype.FuncType([lltype.Signed]*10, lltype.Signed))
    f1ptr = llhelper(F1PTR, f1)
    f2ptr = llhelper(F2PTR, f2)
    f10ptr = llhelper(F10PTR, f10)

    f1_calldescr = cpu.calldescrof(F1PTR.TO, F1PTR.TO.ARGS, F1PTR.TO.RESULT,
                                   EffectInfo.MOST_GENERAL)
    f2_calldescr = cpu.calldescrof(F2PTR.TO, F2PTR.TO.ARGS, F2PTR.TO.RESULT,
                                   EffectInfo.MOST_GENERAL)
    f10_calldescr= cpu.calldescrof(F10PTR.TO, F10PTR.TO.ARGS, F10PTR.TO.RESULT,
                                   EffectInfo.MOST_GENERAL)

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
                arg = longlong.getfloatstorage(arg)
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
        return [longlong.getrealfloat(self.cpu.get_latest_value_float(index))
                for index in range(0, end)]

    def getptr(self, index, T):
        gcref = self.cpu.get_latest_value_ref(index)
        return lltype.cast_opaque_ptr(T, gcref)

    def attach_bridge(self, ops, loop, guard_op_index, looptoken=None, **kwds):
        if looptoken is not None:
            self.namespace = self.namespace.copy()
            self.namespace['looptoken'] = looptoken
        guard_op = loop.operations[guard_op_index]
        assert guard_op.is_guard()
        bridge = self.parse(ops, **kwds)
        assert ([box.type for box in bridge.inputargs] ==
                [box.type for box in guard_op.getfailargs()])
        faildescr = guard_op.getdescr()
        self.cpu.compile_bridge(faildescr, bridge.inputargs, bridge.operations,
                                loop.token)
        return bridge

    def run(self, loop):
        return self.cpu.execute_token(loop.token)

class TestRegallocSimple(BaseTestRegalloc):
    def test_simple_loop(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2) [i1]
        jump(i1)
        '''
        self.interpret(ops, [0])
        assert self.getint(0) == 20

    def test_two_loops_and_a_bridge(self):
        ops = '''
        [i0, i1, i2, i3]
        i4 = int_add(i0, 1)
        i5 = int_lt(i4, 20)
        guard_true(i5) [i4, i1, i2, i3]
        jump(i4, i1, i2, i3)
        '''
        loop = self.interpret(ops, [0, 0, 0, 0])
        ops2 = '''
        [i5]
        i1 = int_add(i5, 1)
        i3 = int_add(i1, 1)
        i4 = int_add(i3, 1)
        i2 = int_lt(i4, 30)
        guard_true(i2) [i4]
        jump(i4)
        '''
        loop2 = self.interpret(ops2, [0])
        bridge_ops = '''
        [i4]
        jump(i4, i4, i4, i4, descr=looptoken)
        '''
        bridge = self.attach_bridge(bridge_ops, loop2, 4, looptoken=loop.token)
        self.cpu.set_future_value_int(0, 0)
        self.run(loop2)
        assert self.getint(0) == 31
        assert self.getint(1) == 30
        assert self.getint(2) == 30
        assert self.getint(3) == 30

    def test_pointer_arg(self):
        ops = '''
        [i0, p0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 10)
        guard_true(i2) [p0]
        jump(i1, p0)
        '''
        S = lltype.GcStruct('S')
        ptr = lltype.malloc(S)
        self.cpu.clear_latest_values(2)
        self.interpret(ops, [0, ptr])
        assert self.getptr(0, lltype.Ptr(S)) == ptr

    def test_exception_bridge_no_exception(self):
        ops = '''
        [i0]
        i1 = same_as(1)
        call(ConstClass(raising_fptr), i0, descr=raising_calldescr)
        guard_exception(ConstClass(zero_division_error)) [i1]
        finish(0)
        '''
        bridge_ops = '''
        [i3]
        i2 = same_as(2)
        guard_no_exception() [i2]
        finish(1)
        '''
        loop = self.interpret(ops, [0])
        assert self.getint(0) == 1
        bridge = self.attach_bridge(bridge_ops, loop, 2)
        self.cpu.set_future_value_int(0, 0)
        self.run(loop)
        assert self.getint(0) == 1

    def test_inputarg_unused(self):
        ops = '''
        [i0]
        finish(1)
        '''
        self.interpret(ops, [0])
        # assert did not explode

    def test_nested_guards(self):
        ops = '''
        [i0, i1]
        guard_true(i0) [i0, i1]
        finish(4)
        '''
        bridge_ops = '''
        [i0, i1]
        guard_true(i0) [i0, i1]
        finish(3)
        '''
        loop = self.interpret(ops, [0, 10])
        assert self.getint(0) == 0
        assert self.getint(1) == 10
        bridge = self.attach_bridge(bridge_ops, loop, 0)
        self.cpu.set_future_value_int(0, 0)
        self.cpu.set_future_value_int(1, 10)
        self.run(loop)
        assert self.getint(0) == 0
        assert self.getint(1) == 10

    def test_nested_unused_arg(self):
        ops = '''
        [i0, i1]
        guard_true(i0) [i0, i1]
        finish(1)
        '''
        loop = self.interpret(ops, [0, 1])
        assert self.getint(0) == 0
        bridge_ops = '''
        [i0, i1]
        finish(1, 2)
        '''
        self.attach_bridge(bridge_ops, loop, 0)
        self.cpu.set_future_value_int(0, 0)
        self.cpu.set_future_value_int(1, 1)
        self.run(loop)

    def test_spill_for_constant(self):
        ops = '''
        [i0, i1, i2, i3]
        i4 = int_add(3, i1)
        i5 = int_lt(i4, 30)
        guard_true(i5) [i0, i4, i2, i3]
        jump(1, i4, 3, 4)
        '''
        self.interpret(ops, [0, 0, 0, 0])
        assert self.getints(4) == [1, 30, 3, 4]

    def test_spill_for_constant_lshift(self):
        ops = '''
        [i0, i2, i1, i3]
        i4 = int_lshift(1, i1)
        i5 = int_add(1, i1)
        i6 = int_lt(i5, 30)
        guard_true(i6) [i4, i5, i2, i3]
        jump(i4, 3, i5, 4)
        '''
        self.interpret(ops, [0, 0, 0, 0])
        assert self.getints(4) == [1<<29, 30, 3, 4]
        ops = '''
        [i0, i1, i2, i3]
        i4 = int_lshift(1, i1)
        i5 = int_add(1, i1)
        i6 = int_lt(i5, 30)
        guard_true(i6) [i4, i5, i2, i3]
        jump(i4, i5, 3, 4)
        '''
        self.interpret(ops, [0, 0, 0, 0])
        assert self.getints(4) == [1<<29, 30, 3, 4]
        ops = '''
        [i0, i3, i1, i2]
        i4 = int_lshift(1, i1)
        i5 = int_add(1, i1)
        i6 = int_lt(i5, 30)
        guard_true(i6) [i4, i5, i2, i3]
        jump(i4, 4, i5, 3)
        '''
        self.interpret(ops, [0, 0, 0, 0])
        assert self.getints(4) == [1<<29, 30, 3, 4]

    def test_result_selected_reg_via_neg(self):
        ops = '''
        [i0, i1, i2, i3]
        i6 = int_neg(i2)
        i7 = int_add(1, i1)
        i4 = int_lt(i7, 10)
        guard_true(i4) [i0, i6, i7]
        jump(1, i7, i2, i6)
        '''
        self.interpret(ops, [0, 0, 3, 0])
        assert self.getints(3) == [1, -3, 10]
        
    def test_compare_memory_result_survives(self):
        ops = '''
        [i0, i1, i2, i3]
        i4 = int_lt(i0, i1)
        i5 = int_add(i3, 1)
        i6 = int_lt(i5, 30)
        guard_true(i6) [i4]
        jump(i0, i1, i4, i5)
        '''
        self.interpret(ops, [0, 10, 0, 0])
        assert self.getint(0) == 1

    def test_jump_different_args(self):
        ops = '''
        [i0, i15, i16, i18, i1, i2, i3]
        i4 = int_add(i3, 1)
        i5 = int_lt(i4, 20)
        guard_true(i5) [i2, i1]
        jump(i0, i18, i15, i16, i2, i1, i4)
        '''
        self.interpret(ops, [0, 1, 2, 3])

    def test_op_result_unused(self):
        ops = '''
        [i0, i1]
        i2 = int_add(i0, i1)
        finish(0)
        '''
        self.interpret(ops, [0, 0])

    def test_guard_value_two_boxes(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7]
        guard_value(i6, i1) [i0, i2, i3, i4, i5, i6]
        finish(i0, i2, i3, i4, i5, i6)
        '''
        self.interpret(ops, [0, 0, 0, 0, 0, 0, 0, 0])
        assert self.getint(0) == 0

    def test_bug_wrong_stack_adj(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8]
        i9 = same_as(0)
        guard_true(i0) [i9, i0, i1, i2, i3, i4, i5, i6, i7, i8]
        finish(1, i0, i1, i2, i3, i4, i5, i6, i7, i8)
        '''
        loop = self.interpret(ops, [0, 1, 2, 3, 4, 5, 6, 7, 8])
        assert self.getint(0) == 0
        bridge_ops = '''
        [i9, i0, i1, i2, i3, i4, i5, i6, i7, i8]
        call(ConstClass(raising_fptr), 0, descr=raising_calldescr)
        finish(i0, i1, i2, i3, i4, i5, i6, i7, i8)
        '''
        self.attach_bridge(bridge_ops, loop, 1)
        for i in range(9):
            self.cpu.set_future_value_int(i, i)
        self.run(loop)
        assert self.getints(9) == range(9)

class TestRegallocCompOps(BaseTestRegalloc):
    
    def test_cmp_op_0(self):
        ops = '''
        [i0, i3]
        i1 = same_as(1)
        i2 = int_lt(i0, 100)
        guard_true(i3) [i1, i2]
        finish(0, i2)
        '''
        self.interpret(ops, [0, 1])
        assert self.getint(0) == 0

class TestRegallocMoreRegisters(BaseTestRegalloc):

    cpu = BaseTestRegalloc.cpu

    S = lltype.GcStruct('S', ('field', lltype.Char))
    fielddescr = cpu.fielddescrof(S, 'field')

    A = lltype.GcArray(lltype.Char)
    arraydescr = cpu.arraydescrof(A)

    namespace = locals().copy()

    def test_int_is_true(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7]
        i10 = int_is_true(i0)
        i11 = int_is_true(i1)
        i12 = int_is_true(i2)
        i13 = int_is_true(i3)
        i14 = int_is_true(i4)
        i15 = int_is_true(i5)
        i16 = int_is_true(i6)
        i17 = int_is_true(i7)
        finish(i10, i11, i12, i13, i14, i15, i16, i17)
        '''
        self.interpret(ops, [0, 42, 12, 0, 13, 0, 0, 3333])
        assert self.getints(8) == [0, 1, 1, 0, 1, 0, 0, 1]

    def test_comparison_ops(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6]
        i10 = int_lt(i0, i1)
        i11 = int_le(i2, i3)
        i12 = int_ge(i4, i5)
        i13 = int_eq(i5, i6)
        i14 = int_gt(i6, i2)
        i15 = int_ne(i2, i6)
        finish(i10, i11, i12, i13, i14, i15)
        '''
        self.interpret(ops, [0, 1, 2, 3, 4, 5, 6])
        assert self.getints(6) == [1, 1, 0, 0, 1, 1]

    def test_strsetitem(self):
        ops = '''
        [p0, i]
        strsetitem(p0, 1, i)
        finish()
        '''
        llstr  = rstr.mallocstr(10)
        self.interpret(ops, [llstr, ord('a')])
        assert llstr.chars[1] == 'a'

    def test_setfield_char(self):
        ops = '''
        [p0, i]
        setfield_gc(p0, i, descr=fielddescr)
        finish()
        '''
        s = lltype.malloc(self.S)
        self.interpret(ops, [s, ord('a')])
        assert s.field == 'a'

    def test_setarrayitem_gc(self):
        ops = '''
        [p0, i]
        setarrayitem_gc(p0, 1, i, descr=arraydescr)
        finish()
        '''
        s = lltype.malloc(self.A, 3)
        self.interpret(ops, [s, ord('a')])
        assert s[1] == 'a'

    def test_division_optimized(self):
        ops = '''
        [i7, i6]
        i18 = int_floordiv(i7, i6)
        i19 = int_xor(i7, i6)
        i21 = int_lt(i19, 0)
        i22 = int_mod(i7, i6)
        i23 = int_is_true(i22)
        i24 = int_eq(i6, 4)
        guard_false(i24) [i18]
        jump(i18, i6)
        '''
        self.interpret(ops, [10, 4])
        assert self.getint(0) == 2
        # FIXME: Verify that i19 - i23 are removed

class TestRegallocFloats(BaseTestRegalloc):
    def test_float_add(self):
        ops = '''
        [f0, f1]
        f2 = float_add(f0, f1)
        finish(f2, f0, f1)
        '''
        self.interpret(ops, [3.0, 1.5])
        assert self.getfloats(3) == [4.5, 3.0, 1.5]

    def test_float_adds_stack(self):
        ops = '''
        [f0, f1, f2, f3, f4, f5, f6, f7, f8]
        f9 = float_add(f0, f1)
        f10 = float_add(f8, 3.5)
        finish(f9, f10, f2, f3, f4, f5, f6, f7, f8)
        '''
        self.interpret(ops, [0.1, .2, .3, .4, .5, .6, .7, .8, .9])
        assert self.getfloats(9) == [.1+.2, .9+3.5, .3, .4, .5, .6, .7, .8, .9]

    def test_lt_const(self):
        ops = '''
        [f0]
        i1 = float_lt(3.5, f0)
        finish(i1)
        '''
        self.interpret(ops, [0.1])
        assert self.getint(0) == 0

    def test_bug_float_is_true_stack(self):
        # NB. float_is_true no longer exists.  Unsure if keeping this test
        # makes sense any more.
        ops = '''
        [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9]
        i0 = float_ne(f0, 0.0)
        i1 = float_ne(f1, 0.0)
        i2 = float_ne(f2, 0.0)
        i3 = float_ne(f3, 0.0)
        i4 = float_ne(f4, 0.0)
        i5 = float_ne(f5, 0.0)
        i6 = float_ne(f6, 0.0)
        i7 = float_ne(f7, 0.0)
        i8 = float_ne(f8, 0.0)
        i9 = float_ne(f9, 0.0)
        finish(i0, i1, i2, i3, i4, i5, i6, i7, i8, i9)
        '''
        loop = self.interpret(ops, [0.0, .1, .2, .3, .4, .5, .6, .7, .8, .9])
        assert self.getints(9) == [0, 1, 1, 1, 1, 1, 1, 1, 1]

class TestRegAllocCallAndStackDepth(BaseTestRegalloc):
    def expected_param_depth(self, num_args):
        # Assumes the arguments are all non-float
        if IS_X86_32:
            return num_args
        elif IS_X86_64:
            return max(num_args - 6, 0)

    def test_one_call(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8, i9]
        i10 = call(ConstClass(f1ptr), i0, descr=f1_calldescr)
        finish(i10, i1, i2, i3, i4, i5, i6, i7, i8, i9)
        '''
        loop = self.interpret(ops, [4, 7, 9, 9 ,9, 9, 9, 9, 9, 9, 9])
        assert self.getints(11) == [5, 7, 9, 9, 9, 9, 9, 9, 9, 9, 9]
        assert loop.token._x86_param_depth == self.expected_param_depth(1)

    def test_two_calls(self):
        ops = '''
        [i0, i1,  i2, i3, i4, i5, i6, i7, i8, i9]
        i10 = call(ConstClass(f1ptr), i0, descr=f1_calldescr)
        i11 = call(ConstClass(f2ptr), i10, i1, descr=f2_calldescr)        
        finish(i11, i1,  i2, i3, i4, i5, i6, i7, i8, i9)
        '''
        loop = self.interpret(ops, [4, 7, 9, 9 ,9, 9, 9, 9, 9, 9, 9])
        assert self.getints(11) == [5*7, 7, 9, 9, 9, 9, 9, 9, 9, 9, 9]
        assert loop.token._x86_param_depth == self.expected_param_depth(2)

    def test_call_many_arguments(self):
        # NB: The first and last arguments in the call are constants. This
        # is primarily for x86-64, to ensure that loading a constant to an
        # argument register or to the stack works correctly
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7]
        i8 = call(ConstClass(f10ptr), 1, i0, i1, i2, i3, i4, i5, i6, i7, 10, descr=f10_calldescr)
        finish(i8)
        '''
        loop = self.interpret(ops, [2, 3, 4, 5, 6, 7, 8, 9])
        assert self.getint(0) == 55
        assert loop.token._x86_param_depth == self.expected_param_depth(10)

    def test_bridge_calls_1(self):
        ops = '''
        [i0, i1]
        i2 = call(ConstClass(f1ptr), i0, descr=f1_calldescr)
        guard_value(i2, 0, descr=fdescr1) [i2, i1]
        finish(i1)
        '''
        loop = self.interpret(ops, [4, 7])
        assert self.getint(0) == 5
        ops = '''
        [i2, i1]
        i3 = call(ConstClass(f2ptr), i2, i1, descr=f2_calldescr)        
        finish(i3, descr=fdescr2)        
        '''
        bridge = self.attach_bridge(ops, loop, -2)

        assert loop.operations[-2].getdescr()._x86_bridge_param_depth == self.expected_param_depth(2)

        self.cpu.set_future_value_int(0, 4)
        self.cpu.set_future_value_int(1, 7)        
        self.run(loop)
        assert self.getint(0) == 5*7

    def test_bridge_calls_2(self):
        ops = '''
        [i0, i1]
        i2 = call(ConstClass(f2ptr), i0, i1, descr=f2_calldescr)
        guard_value(i2, 0, descr=fdescr1) [i2]
        finish(i1)
        '''
        loop = self.interpret(ops, [4, 7])
        assert self.getint(0) == 4*7
        ops = '''
        [i2]
        i3 = call(ConstClass(f1ptr), i2, descr=f1_calldescr)        
        finish(i3, descr=fdescr2)        
        '''
        bridge = self.attach_bridge(ops, loop, -2)

        assert loop.operations[-2].getdescr()._x86_bridge_param_depth == self.expected_param_depth(2)

        self.cpu.set_future_value_int(0, 4)
        self.cpu.set_future_value_int(1, 7)        
        self.run(loop)
        assert self.getint(0) == 29

