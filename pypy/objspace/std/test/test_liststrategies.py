from pypy.objspace.std.listobject import W_ListObject, EmptyListStrategy, ObjectListStrategy, IntegerListStrategy, StringListStrategy
from pypy.objspace.std.test.test_listobject import TestW_ListObject

class TestW_ListStrategies(TestW_ListObject):

    def test_check_strategy(self):
        assert isinstance(W_ListObject([]).strategy, EmptyListStrategy)
        assert isinstance(W_ListObject([self.space.wrap(1),self.space.wrap('a')]).strategy, ObjectListStrategy)
        assert isinstance(W_ListObject([self.space.wrap(1),self.space.wrap(2),self.space.wrap(3)]).strategy, IntegerListStrategy)
        assert isinstance(W_ListObject([self.space.wrap('a'), self.space.wrap('b')]).strategy, StringListStrategy)

    def test_empty_to_any(self):
        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.append(self.space.wrap(1.))
        assert isinstance(l.strategy, ObjectListStrategy)

        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.append(self.space.wrap(1))
        assert isinstance(l.strategy, IntegerListStrategy)

        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.append(self.space.wrap('a'))
        assert isinstance(l.strategy, StringListStrategy)
