
""" Tests for register allocation for common constructs
"""

from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.backend.x86.regalloc import RegAlloc, REGS
from pypy.jit.metainterp.test.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import rclass

class DummyTree(object):
    operations = [ResOperation(rop.FAIL, [], None)]
    inputargs = []

class MockAssembler(object):
    gcrefs = None

class TestRegallocDirect(object):
    def fill_regs(self, regalloc):
        allboxes = []
        for reg in REGS:
            box = BoxInt()
            allboxes.append(box)
            regalloc.reg_bindings[box] = reg
        return allboxes
    
    def test_make_sure_var_in_reg(self):
        regalloc = RegAlloc(MockAssembler(), DummyTree())
        boxes = self.fill_regs(regalloc)
        box = boxes[-1]
        oldloc = regalloc.loc(box)
        newloc = regalloc.make_sure_var_in_reg(box, [])
        assert oldloc is newloc

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

    def interpret(self, ops, args, jump_targets=None):
        loop = self.parse(ops, jump_targets=jump_targets)
        self.cpu.compile_operations(loop)
        for i, arg in enumerate(args):
            if isinstance(arg, int):
                self.cpu.set_future_value_int(i, arg)
            else:
                assert isinstance(lltype.typeOf(arg), lltype.Ptr)
                llgcref = lltype.cast_opaque_ptr(llmemory.GCREF, arg)
                self.cpu.set_future_value_ptr(i, llgcref)
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
