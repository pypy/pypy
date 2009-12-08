
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.backend.x86.test.test_regalloc import BaseTestRegalloc

class TestRecompilation(BaseTestRegalloc):
    def test_compile_bridge_not_deeper(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2, descr=fdescr1) [i1]
        jump(i1)
        '''
        loop = self.interpret(ops, [0])
        assert self.getint(0) == 20
        ops = '''
        [i1]
        i3 = int_add(i1, 1)
        finish(i3, descr=fdescr2)
        '''
        bridge = self.attach_bridge(ops, loop, -2)
        self.cpu.set_future_value_int(0, 0)
        fail = self.run(loop)
        assert fail.identifier == 2
        assert self.getint(0) == 21
    
    def test_compile_bridge_deeper(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2, descr=fdescr1) [i1]
        jump(i1)
        '''
        loop = self.interpret(ops, [0])
        previous = loop.token._x86_frame_depth
        assert loop.token._x86_param_depth == 0
        assert self.getint(0) == 20
        ops = '''
        [i1]
        i3 = int_add(i1, 1)
        i4 = int_add(i3, 1)
        i5 = int_add(i4, 1)
        i6 = int_add(i5, 1)
        i7 = int_add(i5, i4)
        i8 = int_add(i7, 1)
        i9 = int_add(i8, 1)
        finish(i3, i4, i5, i6, i7, i8, i9, descr=fdescr2)
        '''
        bridge = self.attach_bridge(ops, loop, -2)
        descr = loop.operations[2].descr
        new = descr._x86_bridge_frame_depth
        assert descr._x86_bridge_param_depth == 0        
        assert new > previous
        self.cpu.set_future_value_int(0, 0)
        fail = self.run(loop)
        assert fail.identifier == 2
        assert self.getint(0) == 21
        assert self.getint(1) == 22
        assert self.getint(2) == 23
        assert self.getint(3) == 24

    def test_bridge_jump_to_other_loop(self):
        loop = self.interpret('''
        [i0, i10, i11, i12, i13, i14, i15, i16]
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2, descr=fdescr1) [i1]
        jump(i1, i10, i11, i12, i13, i14, i15, i16)
        ''', [0])
        other_loop = self.interpret('''
        [i3]
        guard_false(i3, descr=fdescr2) [i3]
        jump(i3)
        ''', [1])
        ops = '''
        [i3]
        jump(i3, 1, 2, 3, 4, 5, 6, 7, descr=looptoken)
        '''
        bridge = self.attach_bridge(ops, other_loop, 0, looptoken=loop.token)
        self.cpu.set_future_value_int(0, 1)
        fail = self.run(other_loop)
        assert fail.identifier == 1

    def test_bridge_jumps_to_self_deeper(self):
        loop = self.interpret('''
        [i0, i1, i2, i31, i32, i33]
        i98 = same_as(0)
        i99 = same_as(1)
        i30 = int_add(i1, i2)
        i3 = int_add(i0, 1)
        i4 = int_and(i3, 1)
        guard_false(i4) [i98, i3]
        i5 = int_lt(i3, 20)
        guard_true(i5) [i99, i3]
        jump(i3, i30, 1, i30, i30, i30)
        ''', [0])
        assert self.getint(0) == 0
        assert self.getint(1) == 1
        ops = '''
        [i97, i3]
        i10 = int_mul(i3, 2)
        i8 = int_add(i3, 1)
        i6 = int_add(i8, i10)
        i7 = int_add(i3, i6)
        i12 = int_add(i7, i8)
        i11 = int_add(i12, i6)
        jump(i3, i12, i11, i10, i6, i7, descr=looptoken)
        '''
        bridge = self.attach_bridge(ops, loop, 5, looptoken=loop.token)
        guard_op = loop.operations[5]
        loop_frame_depth = loop.token._x86_frame_depth
        assert loop.token._x86_param_depth == 0
        assert guard_op.descr._x86_bridge_frame_depth > loop_frame_depth
        assert guard_op.descr._x86_bridge_param_depth == 0
        self.cpu.set_future_value_int(0, 0)
        self.cpu.set_future_value_int(1, 0)
        self.cpu.set_future_value_int(2, 0)
        self.run(loop)
        assert self.getint(0) == 1
        assert self.getint(1) == 20

    def test_bridge_jumps_to_self_shallower(self):
        loop = self.interpret('''
        [i0, i1, i2]
        i98 = same_as(0)
        i99 = same_as(1)
        i3 = int_add(i0, 1)
        i4 = int_and(i3, 1)
        guard_false(i4) [i98, i3]
        i5 = int_lt(i3, 20)
        guard_true(i5) [i99, i3]
        jump(i3, i1, i2)
        ''', [0])
        assert self.getint(0) == 0
        assert self.getint(1) == 1
        ops = '''
        [i97, i3]
        jump(i3, 0, 1, descr=looptoken)
        '''
        bridge = self.attach_bridge(ops, loop, 4, looptoken=loop.token)
        self.cpu.set_future_value_int(0, 0)
        self.cpu.set_future_value_int(1, 0)
        self.cpu.set_future_value_int(2, 0)
        self.run(loop)
        assert self.getint(0) == 1
        assert self.getint(1) == 20
        
