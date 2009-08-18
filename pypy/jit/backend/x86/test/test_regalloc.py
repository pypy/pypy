
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
