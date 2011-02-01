from pypy.objspace.std.listobject import W_ListObject, EmptyListStrategy, ObjectListStrategy
from pypy.objspace.std.test.test_listobject import TestW_ListObject

class TestW_ListStrategies(TestW_ListObject):

    def test_check_strategy(self):
        assert isinstance(W_ListObject([]).strategy, EmptyListStrategy)
        assert isinstance(W_ListObject([1]).strategy, ObjectListStrategy)
