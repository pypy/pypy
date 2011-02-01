from pypy.objspace.std.listobject import W_ListObject, EmptyListStrategy, ObjectListStrategy
from pypy.objspace.std.test.test_listobject import TestW_ListObject

class TestW_ListStrategies(TestW_ListObject):

    def test_check_strategy(self):
        assert isinstance(W_ListObject([]).strategy, EmptyListStrategy)
        assert isinstance(W_ListObject([self.space.wrap(1),self.space.wrap('a')]).strategy, ObjectListStrategy)
        assert isinstance(W_ListObject([self.space.wrap(1),self.space.wrap(2),self.space.wrap(3)]).strategy, ObjectListStrategy)
        assert isinstance(W_ListObject([self.space.wrap('a'), self.space.wrap('b')]).strategy, ObjectListStrategy)

    def test_switch_strategy(self):
        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.append(self.space.wrap(1))
        assert isinstance(l.strategy, ObjectListStrategy)
