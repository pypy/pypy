
""" Tests for register allocation for common constructs
"""

from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.test.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import llhelper

class TestRegalloc(object):
    cpu = CPU(None, None)

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

    def getptr(self, index, T):
        gcref = self.cpu.get_latest_value_ptr(index)
        return lltype.cast_opaque_ptr(T, gcref)

    def attach_bridge(self, ops, loop, guard_op):
        assert guard_op.is_guard()
        bridge = self.parse(ops)
        guard_op.suboperations = bridge.operations
        self.cpu.compile_operations(loop, guard_op)
        return bridge

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
