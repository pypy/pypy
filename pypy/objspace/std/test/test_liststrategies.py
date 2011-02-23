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

    def test_int_to_any(self):
        l = W_ListObject([self.space.wrap(1),self.space.wrap(2),self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.append(self.space.wrap(4))
        assert isinstance(l.strategy, IntegerListStrategy)
        l.append(self.space.wrap('a'))
        assert isinstance(l.strategy, ObjectListStrategy)

    def test_string_to_any(self):
        l = W_ListObject([self.space.wrap('a'),self.space.wrap('b'),self.space.wrap('c')])
        assert isinstance(l.strategy, StringListStrategy)
        l.append(self.space.wrap('d'))
        assert isinstance(l.strategy, StringListStrategy)
        l.append(self.space.wrap(3))
        assert isinstance(l.strategy, ObjectListStrategy)

    def test_setitem(self):
        # This should work if test_listobject.py passes
        l = W_ListObject([self.space.wrap('a'),self.space.wrap('b'),self.space.wrap('c')])
        assert self.space.eq_w(l.getitem(0), self.space.wrap('a'))
        l.setitem(0, self.space.wrap('d'))
        assert self.space.eq_w(l.getitem(0), self.space.wrap('d'))

        assert isinstance(l.strategy, StringListStrategy)

        # IntStrategy to ObjectStrategy
        l = W_ListObject([self.space.wrap(1),self.space.wrap(2),self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.setitem(0, self.space.wrap('d'))
        assert isinstance(l.strategy, ObjectListStrategy)

        # StringStrategy to ObjectStrategy
        l = W_ListObject([self.space.wrap('a'),self.space.wrap('b'),self.space.wrap('c')])
        assert isinstance(l.strategy, StringListStrategy)
        l.setitem(0, self.space.wrap(2))
        assert isinstance(l.strategy, ObjectListStrategy)

    def test_insert(self):
        # no change
        l = W_ListObject([self.space.wrap(1),self.space.wrap(2),self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.insert(3, self.space.wrap(4))
        assert isinstance(l.strategy, IntegerListStrategy)

        # StringStrategy
        l = W_ListObject([self.space.wrap('a'),self.space.wrap('b'),self.space.wrap('c')])
        assert isinstance(l.strategy, StringListStrategy)
        l.insert(3, self.space.wrap(2))
        assert isinstance(l.strategy, ObjectListStrategy)

        # IntegerStrategy
        l = W_ListObject([self.space.wrap(1),self.space.wrap(2),self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.insert(3, self.space.wrap('d'))
        assert isinstance(l.strategy, ObjectListStrategy)

        # EmptyStrategy
        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.insert(0, self.space.wrap('a'))
        assert isinstance(l.strategy, StringListStrategy)

        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.insert(0, self.space.wrap(2))
        assert isinstance(l.strategy, IntegerListStrategy)

    def test_delete(self):
        l = W_ListObject([self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.deleteitem(0)
        assert isinstance(l.strategy, EmptyListStrategy)

        l = W_ListObject([self.space.wrap(1), self.space.wrap(2)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.deleteslice(0, 1, 2)
        assert isinstance(l.strategy, EmptyListStrategy)

    def test_setslice(self):
        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.setslice(0, 1, 2, [self.space.wrap(1), self.space.wrap(2), self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)

        l = W_ListObject([self.space.wrap(1), self.space.wrap(2), self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.setslice(0, 1, 2, [self.space.wrap(4), self.space.wrap(5), self.space.wrap(6)])
        assert isinstance(l.strategy, IntegerListStrategy)

        l = W_ListObject([self.space.wrap(1), self.space.wrap('b'), self.space.wrap(3)])
        assert isinstance(l.strategy, ObjectListStrategy)
        l.setslice(0, 1, 2, [self.space.wrap(1), self.space.wrap(2), self.space.wrap(3)])
        assert isinstance(l.strategy, ObjectListStrategy)

        l = W_ListObject([self.space.wrap(1), self.space.wrap(2), self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.setslice(0, 1, 2, [self.space.wrap('a'), self.space.wrap('b'), self.space.wrap('c')])
        assert isinstance(l.strategy, ObjectListStrategy)

    def test_extend(self):
        l = W_ListObject([])
        assert isinstance(l.strategy, EmptyListStrategy)
        l.extend(W_ListObject([self.space.wrap(1), self.space.wrap(2), self.space.wrap(3)]))
        assert isinstance(l.strategy, IntegerListStrategy)

        l = W_ListObject([self.space.wrap(1), self.space.wrap(2), self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.extend(W_ListObject([self.space.wrap('a'), self.space.wrap('b'), self.space.wrap('c')]))
        assert isinstance(l.strategy, ObjectListStrategy)

        l = W_ListObject([self.space.wrap(1), self.space.wrap(2), self.space.wrap(3)])
        assert isinstance(l.strategy, IntegerListStrategy)
        l.extend(W_ListObject([self.space.wrap(4), self.space.wrap(5), self.space.wrap(6)]))
        assert isinstance(l.strategy, IntegerListStrategy)

