from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin)
from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import (
    BaseTestBasic)
from rpython.jit.metainterp.history import ConstInt, ConstPtr

class TestCompatible(BaseTestBasic, LLtypeMixin):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap"

    def test_guard_compatible_after_guard_value(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

    def test_guard_compatible_after_guard_compatible(self):
        ops = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

    def test_guard_compatible_call_pure(self):
        call_pure_results = {
            (ConstInt(123), ConstPtr(self.myptr)): ConstInt(5),
        }
        ops = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        i3 = call_pure_i(123, p1, descr=plaincalldescr)
        escape_n(i3)
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        escape_n(5)
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected, call_pure_results=call_pure_results)
