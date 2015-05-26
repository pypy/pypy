import py

from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp.optimizeopt.test.test_dependency import DependencyBaseTest

class SchedulerBaseTest(DependencyBaseTest):

    def test_schedule_split_arith(self):
        pass


class TestLLType(SchedulerBaseTest, LLtypeMixin):
    pass
