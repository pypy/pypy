
""" Tests for register allocation for common constructs
"""

from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.backend.x86.regalloc import RegAlloc, REGS, WORD
from pypy.jit.metainterp.test.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import rclass, rstr
from pypy.jit.backend.x86.ri386 import *

class DummyTree(object):
    operations = [ResOperation(rop.FAIL, [], None)]
    inputargs = []

class MockAssembler(object):
    gcrefs = None

    def __init__(self):
        self.loads = []
        self.stores = []
        self.performs = []
        self.lea = []

    def dump(self, *args):
        pass

    def regalloc_load(self, from_loc, to_loc):
        self.loads.append((from_loc, to_loc))

    def regalloc_store(self, from_loc, to_loc):
        self.stores.append((from_loc, to_loc))

    def regalloc_perform(self, op, arglocs, resloc):
        self.performs.append((op, arglocs, resloc))

    def regalloc_perform_discard(self, op, arglocs):
        self.performs.append((op, arglocs))

    def load_effective_addr(self, *args):
        self.lea.append(args)

class RegAllocForTests(RegAlloc):
    position = 0
    def _compute_next_usage(self, v, _):
        return -1

class TestRegallocDirect(object):
    def fill_regs(self, regalloc):
        allboxes = []
        for reg in REGS:
            box = BoxInt()
            allboxes.append(box)
            regalloc.reg_bindings[box] = reg
        regalloc.free_regs = []
        return allboxes
    
    def test_make_sure_var_in_reg(self):
        regalloc = RegAlloc(MockAssembler(), DummyTree())
        boxes = self.fill_regs(regalloc)
        box = boxes[-1]
        oldloc = regalloc.loc(box)
        newloc = regalloc.make_sure_var_in_reg(box, [])
        assert oldloc is newloc
        regalloc._check_invariants()

    def test_make_sure_var_in_reg_need_lower_byte(self):
        regalloc = RegAlloc(MockAssembler(), DummyTree())
        box = BoxInt()
        regalloc.reg_bindings[box] = edi
        regalloc.free_regs.remove(edi)
        loc = regalloc.make_sure_var_in_reg(box, [], need_lower_byte=True)
        assert loc is not edi and loc is not esi
        assert len(regalloc.assembler.loads) == 1
        regalloc._check_invariants()

    def test_make_sure_var_in_reg_need_lower_byte_no_free_reg(self):
        regalloc = RegAllocForTests(MockAssembler(), DummyTree())
        box = BoxInt()
        regalloc.reg_bindings = {BoxInt(): eax, BoxInt(): ebx, BoxInt(): ecx,
                                 BoxInt(): edx, box:edi}
        regalloc.free_regs = [esi]
        regalloc._check_invariants()
        loc = regalloc.make_sure_var_in_reg(box, [], need_lower_byte=True)
        assert loc is not edi and loc is not esi
        assert len(regalloc.assembler.loads) == 1
        regalloc._check_invariants()

    def test_make_sure_var_in_reg_mem(self):
        regalloc = RegAlloc(MockAssembler(), DummyTree())
        box = BoxInt()
        regalloc.stack_loc(box)
        loc = regalloc.make_sure_var_in_reg(box, [], need_lower_byte=True)
        assert loc is not edi and loc is not esi
        assert len(regalloc.assembler.loads) == 1        
        regalloc._check_invariants()

    def test_registers_around_call(self):
        cpu = CPU(None, None)
        regalloc = RegAlloc(MockAssembler(), DummyTree())
        boxes = self.fill_regs(regalloc)
        TP = lltype.FuncType([], lltype.Void)
        calldescr = cpu.calldescrof(TP, TP.ARGS, TP.RESULT)
        regalloc._check_invariants()
        box = boxes[0]
        for box in boxes:
            regalloc.longevity[box] = (0, 1)
        regalloc.position = 0
        regalloc.consider_call(ResOperation(rop.CALL, [box], None, calldescr),
                               None)
        assert len(regalloc.assembler.stores) == 3
        regalloc._check_invariants()

    def test_registers_around_newstr(self):
        cpu = CPU(None, None)
        regalloc = RegAllocForTests(MockAssembler(), DummyTree())
        regalloc.assembler.cpu = cpu
        boxes = self.fill_regs(regalloc)
        regalloc._check_invariants()
        for box in boxes:
            regalloc.longevity[box] = (0, 1)
        regalloc.position = 0
        resbox = BoxInt()
        regalloc.longevity[resbox] = (1, 1)
        regalloc.consider_newstr(ResOperation(rop.NEWSTR, [box], resbox,
                                              None), None)
        regalloc._check_invariants()

class BaseTestRegalloc(object):
    cpu = CPU(None, None)

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
    raising_calldescr = cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT)

    namespace = locals().copy()
    type_system = 'lltype'

    def parse(self, s, boxkinds=None, jump_targets=None):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system,
                     jump_targets=jump_targets,
                     boxkinds=boxkinds)

    def interpret(self, ops, args, jump_targets=None, run=True):
        loop = self.parse(ops, jump_targets=jump_targets)
        self.cpu.compile_operations(loop)
        for i, arg in enumerate(args):
            if isinstance(arg, int):
                self.cpu.set_future_value_int(i, arg)
            else:
                assert isinstance(lltype.typeOf(arg), lltype.Ptr)
                llgcref = lltype.cast_opaque_ptr(llmemory.GCREF, arg)
                self.cpu.set_future_value_ptr(i, llgcref)
        if run:
            self.cpu.execute_operations(loop)
        return loop

    def getint(self, index):
        return self.cpu.get_latest_value_int(index)

    def getints(self, end):
        return [self.cpu.get_latest_value_int(index) for
                index in range(0, end)]

    def getptr(self, index, T):
        gcref = self.cpu.get_latest_value_ptr(index)
        return lltype.cast_opaque_ptr(T, gcref)

    def attach_bridge(self, ops, loop, guard_op):
        assert guard_op.is_guard()
        bridge = self.parse(ops)
        guard_op.suboperations = bridge.operations
        self.cpu.compile_operations(loop, guard_op)
        return bridge


class TestRegallocSimple(BaseTestRegalloc):
    def test_simple_loop(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2)
           fail(i1)
        jump(i1)
        '''
        self.interpret(ops, [0])
        assert self.getint(0) == 20

    def test_compile_and_recompile(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2)
           fail(i1)
        jump(i1)
        '''
        loop = self.interpret(ops, [0])
        assert self.getint(0) == 20
        ops = '''
        [i1]
        i3 = int_add(i1, 1)
        i4 = int_add(i3, 1)
        i5 = int_add(i4, 1)
        i6 = int_add(i5, 1)
        fail(i3, i4, i5, i6)
        '''
        bridge = self.attach_bridge(ops, loop, loop.operations[-2])
        self.cpu.set_future_value_int(0, 0)
        op = self.cpu.execute_operations(loop)
        assert op is bridge.operations[-1]
        assert self.getint(0) == 21
        assert self.getint(1) == 22
        assert self.getint(2) == 23
        assert self.getint(3) == 24

    def test_two_loops_and_a_bridge(self):
        ops = '''
        [i0, i1, i2, i3]
        i4 = int_add(i0, 1)
        i5 = int_lt(i4, 20)
        guard_true(i5)
           fail(i4, i1, i2, i3)
        jump(i4, i1, i2, i3)
        '''
        loop = self.interpret(ops, [0])
        ops2 = '''
        [i5]
        i1 = int_add(i5, 1)
        i3 = int_add(i1, 1)
        i4 = int_add(i3, 1)
        i2 = int_lt(i4, 30)
        guard_true(i2)
           jump(i4, i4, i4, i4)
        jump(i4)
        '''
        loop2 = self.interpret(ops2, [0], jump_targets=[loop, 'self'])
        assert self.getint(0) == 31
        assert self.getint(1) == 30
        assert self.getint(2) == 30
        assert self.getint(3) == 30

    def test_pointer_arg(self):
        ops = '''
        [i0, p0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 10)
        guard_true(i2)
            fail(p0)
        jump(i1, p0)
        '''
        S = lltype.GcStruct('S')
        ptr = lltype.malloc(S)
        self.interpret(ops, [0, ptr])
        assert self.getptr(0, lltype.Ptr(S)) == ptr
        assert not self.cpu.assembler.fail_boxes_ptr[0]
        assert not self.cpu.assembler.fail_boxes_ptr[1]

    def test_exception_bridge_no_exception(self):

        
        ops = '''
        [i0]
        call(ConstClass(raising_fptr), i0, descr=raising_calldescr)
        guard_exception(ConstClass(zero_division_error))
            guard_no_exception()
                fail(2)
            fail(1)
        fail(0)
        '''
        self.interpret(ops, [0])
        assert self.getint(0) == 1

    def test_inputarg_unused(self):
        ops = '''
        [i0]
        fail(1)
        '''
        self.interpret(ops, [0])
        # assert did not explode

    def test_nested_guards(self):
        ops = '''
        [i0, i1]
        guard_true(i0)
            guard_true(i0)
                fail(i0, i1)
            fail(3)
        fail(4)
        '''
        self.interpret(ops, [0, 10])
        assert self.getint(0) == 0
        assert self.getint(1) == 10

    def test_spill_for_constant(self):
        ops = '''
        [i0, i1, i2, i3]
        i4 = int_add(3, i1)
        i5 = int_lt(i4, 30)
        guard_true(i5)
            fail(i0, i4, i2, i3)
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
        guard_true(i6)
            fail(i4, i5, i2, i3)
        jump(i4, 3, i5, 4)
        '''
        self.interpret(ops, [0, 0, 0, 0])
        assert self.getints(4) == [1<<29, 30, 3, 4]
        ops = '''
        [i0, i1, i2, i3]
        i4 = int_lshift(1, i1)
        i5 = int_add(1, i1)
        i6 = int_lt(i5, 30)
        guard_true(i6)
            fail(i4, i5, i2, i3)
        jump(i4, i5, 3, 4)
        '''
        self.interpret(ops, [0, 0, 0, 0])
        assert self.getints(4) == [1<<29, 30, 3, 4]
        ops = '''
        [i0, i3, i1, i2]
        i4 = int_lshift(1, i1)
        i5 = int_add(1, i1)
        i6 = int_lt(i5, 30)
        guard_true(i6)
            fail(i4, i5, i2, i3)
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
        guard_true(i4)
            fail(i0, i6, i7)
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
        guard_true(i6)
            fail(i4)
        jump(i0, i1, i4, i5)
        '''
        self.interpret(ops, [0, 10, 0, 0])
        assert self.getint(0) == 1

    def test_jump_different_args(self):
        ops = '''
        [i0, i15, i16, i18, i1, i2, i3]
        i4 = int_add(i3, 1)
        i5 = int_lt(i4, 20)
        guard_true(i5)
            fail(i2, i1)
        jump(i0, i18, i15, i16, i2, i1, i4)
        '''
        self.interpret(ops, [0, 1, 2, 3])

    def test_op_result_unused(self):
        ops = '''
        [i0, i1]
        i2 = int_add(i0, i1)
        fail(0)
        '''
        self.interpret(ops, [0, 0])

    def test_guard_value_two_boxes(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7]
        guard_value(i6, i1)
           fail(i0, i2, i3, i4, i5, i6)
        fail(i0, i2, i3, i4, i5, i6)
        '''
        self.interpret(ops, [0, 0, 0, 0, 0, 0, 0, 0])
        assert self.getint(0) == 0

class TestRegallocCompOps(BaseTestRegalloc):
    
    def test_cmp_op_0(self):
        ops = '''
        [i0, i3]
        i2 = int_lt(i0, 100)
        guard_true(i3)
           fail(1, i2)
        fail(0, i2)
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
        fail(i10, i11, i12, i13, i14, i15, i16, i17)
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
        fail(i10, i11, i12, i13, i14, i15)
        '''
        self.interpret(ops, [0, 1, 2, 3, 4, 5, 6])
        assert self.getints(6) == [1, 1, 0, 0, 1, 1]

    def test_nullity(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6]
        i10 = oononnull(i0)
        i11 = ooisnull(i1)
        i12 = oononnull(i2)
        i13 = oononnull(i3)
        i14 = ooisnull(i6)
        i15 = ooisnull(i5)
        fail(i10, i11, i12, i13, i14, i15)
        '''
        self.interpret(ops, [0, 1, 2, 3, 4, 5, 6])
        assert self.getints(6) == [0, 0, 1, 1, 0, 0]

    def test_strsetitem(self):
        ops = '''
        [p0, i]
        strsetitem(p0, 1, i)
        fail()
        '''
        llstr  = rstr.mallocstr(10)
        self.interpret(ops, [llstr, ord('a')])
        assert llstr.chars[1] == 'a'

    def test_setfield_char(self):
        ops = '''
        [p0, i]
        setfield_gc(p0, i, descr=fielddescr)
        fail()
        '''
        s = lltype.malloc(self.S)
        self.interpret(ops, [s, ord('a')])
        assert s.field == 'a'

    def test_setarrayitem_gc(self):
        ops = '''
        [p0, i]
        setarrayitem_gc(p0, 1, i, descr=arraydescr)
        fail()
        '''
        s = lltype.malloc(self.A, 3)
        self.interpret(ops, [s, ord('a')])
        assert s[1] == 'a'
        

class GcRootMap(object):
    def initialize(self):
        pass

class MockGcDescr(object):
    def get_funcptr_for_new(self):
        return 123
    get_funcptr_for_newarray = get_funcptr_for_new
    get_funcptr_for_newstr = get_funcptr_for_new
    get_funcptr_for_newunicode = get_funcptr_for_new
    
    moving_gc = True
    class GcRefList(object):
        MAXLEN = 1000
        
        def __init__(self):
            TP = rffi.CArray(llmemory.GCREF)
            self.l = lltype.malloc(TP, self.MAXLEN, flavor='raw')
            self.size = 0
        
        def get_address_of_gcref(self, addr):
            baseaddr = rffi.cast(lltype.Signed, self.l)
            for i in range(self.size):
                if self.l[i] == addr:
                    return baseaddr + i * WORD
            self.l[self.size] = addr
            self.size += 1
            return baseaddr + (self.size - 1) * WORD

    gcrootmap = GcRootMap()

class TestRegallocGc(BaseTestRegalloc):
    cpu = CPU(None, None)
    cpu.gc_ll_descr = MockGcDescr()
    cpu.gcrefs = cpu.gc_ll_descr.GcRefList()

    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('field', lltype.Ptr(S)),
                             ('int', lltype.Signed)))

    fielddescr = cpu.fielddescrof(S, 'field')

    struct_ptr = lltype.malloc(S)
    struct_ref = lltype.cast_opaque_ptr(llmemory.GCREF, struct_ptr)
    child_ptr = lltype.nullptr(S)
    struct_ptr.field = child_ptr


    descr0 = cpu.fielddescrof(S, 'int')
    ptr0 = struct_ref

    namespace = locals().copy()

    def test_basic(self):
        ops = '''
        [p0]
        p1 = getfield_gc(p0, descr=fielddescr)
        fail(p1)
        '''
        self.interpret(ops, [self.struct_ptr])
        assert not self.getptr(0, lltype.Ptr(self.S))

    def test_rewrite_constptr(self):
        ops = '''
        []
        p1 = getfield_gc(ConstPtr(struct_ref), descr=fielddescr)
        fail(p1)
        '''
        self.interpret(ops, [])
        assert not self.getptr(0, lltype.Ptr(self.S))
        
    def test_rewrite_constptr_in_brdige(self):
        ops = '''
        [i0]
        guard_true(i0)
            p1 = getfield_gc(ConstPtr(struct_ref), descr=fielddescr)
            fail(p1)
        fail(0)
        '''
        self.interpret(ops, [0])
        assert not self.getptr(0, lltype.Ptr(self.S))

    def test_get_rid_of_debug_merge_point(self):
        ops = '''
        []
        debug_merge_point()
        fail()
        '''
        loop = self.interpret(ops, [], run=False)
        assert len(loop.operations) == 1

    def test_bug_0(self):
        ops = '''
        [i0, i1, i2, i3, i4, i5, i6, i7, i8]
        guard_value(i2, 1)
            fail(i2, i3, i4, i5, i6, i7, i0, i1, i8)
        guard_class(i4, 138998336)
            fail(i4, i5, i6, i7, i0, i1, i8)
        i11 = getfield_gc(i4, descr=descr0)
        i12 = ooisnull(i11)
        guard_false(i12)
            fail(i4, i5, i6, i7, i0, i1, i11, i8)
        i13 = getfield_gc(i11, descr=descr0)
        i14 = ooisnull(i13)
        guard_true(i14)
            fail(i4, i5, i6, i7, i0, i1, i11, i8)
        i15 = getfield_gc(i4, descr=descr0)
        i17 = int_lt(i15, 0)
        guard_false(i17)
            fail(i4, i5, i6, i7, i0, i1, i11, i15, i8)
        i18 = getfield_gc(i11, descr=descr0)
        i19 = int_ge(i15, i18)
        guard_false(i19)
            fail(i4, i5, i6, i7, i0, i1, i11, i15, i8)
        i20 = int_lt(i15, 0)
        guard_false(i20)
            fail(i4, i5, i6, i7, i0, i1, i11, i15, i8)
        i21 = getfield_gc(i11, descr=descr0)
        i22 = getfield_gc(i11, descr=descr0)
        i23 = int_mul(i15, i22)
        i24 = int_add(i21, i23)
        i25 = getfield_gc(i4, descr=descr0)
        i27 = int_add(i25, 1)
        setfield_gc(i4, i27, descr=descr0)
        i29 = getfield_raw(144839744, descr=descr0)
        i31 = int_and(i29, -2141192192)
        i32 = int_is_true(i31)
        guard_false(i32)
            fail(i4, i6, i7, i0, i1, i24)
        i33 = getfield_gc(i0, descr=descr0)
        guard_value(i33, ConstPtr(ptr0))
            fail(i4, i6, i7, i0, i1, i33, i24)
        jump(i0, i1, 1, 17, i4, ConstPtr(ptr0), i6, i7, i24)
        '''
        self.interpret(ops, [0, 0, 0, 0, 0, 0, 0, 0, 0], run=False)
