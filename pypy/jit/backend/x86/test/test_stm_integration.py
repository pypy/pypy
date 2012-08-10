
""" Tests for register allocation for common constructs
"""

import py
from pypy.jit.backend.x86.test.test_regalloc import BaseTestRegalloc


class TestStm(BaseTestRegalloc):

    def test_stm_read_before_spills_all(self):
        # for now, stm_read_before() first spills all registers
        ops = '''
        [i1, i2, p1]
        i3 = int_add(i1, i2)
        stm_read_before(p1, descr=wbdescr)
        escape(i3)         # assert i3 was spilled
        finish(i3)
        '''
        self.interpret(ops, [40, 2])
        res = self.cpu.get_latest_value_int(0)
        assert res == 42
