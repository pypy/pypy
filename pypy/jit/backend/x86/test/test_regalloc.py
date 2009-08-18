
""" Tests for register allocation for common constructs
"""

from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.x86.runner import CPU
from pypy.jit.metainterp.test.oparser import parse
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.annlowlevel import llhelper

class TestRegalloc(object):
    cpu = CPU(None, None)

    namespace = locals().copy()
    type_system = 'lltype'

    def parse(self, s, boxkinds=None):
        return parse(s, self.cpu, self.namespace,
                     type_system=self.type_system,
                     boxkinds=boxkinds)

    def interpret(self, ops, args):
        loop = self.parse(ops)
        self.cpu.compile_operations(loop)
        for i, arg in enumerate(args):
            if isinstance(arg, int):
                self.cpu.set_future_value_int(i, arg)
            else:
                raise NotImplementedError("Arg: %s" % arg)
        self.cpu.execute_operations(loop)
        return loop

    def getint(self, index):
        return self.cpu.get_latest_value_int(index)

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
        bridge = self.parse(ops)
        guard_op = loop.operations[-2]
        guard_op.suboperations = bridge.operations
        self.cpu.compile_operations(loop, guard_op)
        self.cpu.set_future_value_int(0, 0)
        op = self.cpu.execute_operations(loop)
        assert op is bridge.operations[-1]
        assert self.getint(0) == 21
        assert self.getint(1) == 22
        assert self.getint(2) == 23
        assert self.getint(3) == 24
        
