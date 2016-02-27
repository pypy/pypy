import sys
from pypy.objspace.std.setobject import W_SetObject
from pypy.objspace.std.setobject import (
    BytesIteratorImplementation, BytesSetStrategy, EmptySetStrategy,
    IntegerIteratorImplementation, IntegerSetStrategy, ObjectSetStrategy,
    UnicodeIteratorImplementation, UnicodeSetStrategy)
from pypy.objspace.std.listobject import W_ListObject


from hypothesis import strategies, given

ints = strategies.integers(-sys.maxint-1, sys.maxint)
intlists = strategies.lists(ints)

class TestW_SetStrategies:

    def wrapped(self, l):
        return W_ListObject(self.space, [self.space.wrap(x) for x in l])

    def test_from_list(self):
        s = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        assert s.strategy is self.space.fromcache(IntegerSetStrategy)

        s = W_SetObject(self.space, self.wrapped([1,"two",3,"four",5]))
        assert s.strategy is self.space.fromcache(ObjectSetStrategy)

        s = W_SetObject(self.space)
        assert s.strategy is self.space.fromcache(EmptySetStrategy)

        s = W_SetObject(self.space, self.wrapped([]))
        assert s.strategy is self.space.fromcache(EmptySetStrategy)

        s = W_SetObject(self.space, self.wrapped(["a", "b"]))
        assert s.strategy is self.space.fromcache(BytesSetStrategy)

        s = W_SetObject(self.space, self.wrapped([u"a", u"b"]))
        assert s.strategy is self.space.fromcache(UnicodeSetStrategy)

    def test_switch_to_object(self):
        s = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s.add(self.space.wrap("six"))
        assert s.strategy is self.space.fromcache(ObjectSetStrategy)

        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s2 = W_SetObject(self.space, self.wrapped(["six", "seven"]))
        s1.update(s2)
        assert s1.strategy is self.space.fromcache(ObjectSetStrategy)

    def test_switch_to_unicode(self):
        s = W_SetObject(self.space, self.wrapped([]))
        s.add(self.space.wrap(u"six"))
        assert s.strategy is self.space.fromcache(UnicodeSetStrategy)

    def test_symmetric_difference(self):
        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s2 = W_SetObject(self.space, self.wrapped(["six", "seven"]))
        s1.symmetric_difference_update(s2)
        assert s1.strategy is self.space.fromcache(ObjectSetStrategy)

    def test_intersection(self):
        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s2 = W_SetObject(self.space, self.wrapped([4,5, "six", "seven"]))
        s3 = s1.intersect(s2)
        skip("for now intersection with ObjectStrategy always results in another ObjectStrategy")
        assert s3.strategy is self.space.fromcache(IntegerSetStrategy)

    def test_clear(self):
        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s1.clear()
        assert s1.strategy is self.space.fromcache(EmptySetStrategy)

    def test_remove(self):
        s1 = W_SetObject(self.space, self.wrapped([1]))
        self.space.call_method(s1, 'remove', self.space.wrap(1))
        assert s1.strategy is self.space.fromcache(EmptySetStrategy)

    def test_union(self):
        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s2 = W_SetObject(self.space, self.wrapped([4,5,6,7]))
        s3 = W_SetObject(self.space, self.wrapped([4,'5','6',7]))
        s4 = s1.descr_union(self.space, [s2])
        s5 = s1.descr_union(self.space, [s3])
        assert s4.strategy is self.space.fromcache(IntegerSetStrategy)
        assert s5.strategy is self.space.fromcache(ObjectSetStrategy)

    def test_discard(self):
        class FakeInt(object):
            def __init__(self, value):
                self.value = value
            def __hash__(self):
                return hash(self.value)
            def __eq__(self, other):
                if other == self.value:
                    return True
                return False

        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s1.descr_discard(self.space, self.space.wrap("five"))
        skip("currently not supported")
        assert s1.strategy is self.space.fromcache(IntegerSetStrategy)

        set_discard__Set_ANY(self.space, s1, self.space.wrap(FakeInt(5)))
        assert s1.strategy is self.space.fromcache(ObjectSetStrategy)

    def test_has_key(self):
        class FakeInt(object):
            def __init__(self, value):
                self.value = value
            def __hash__(self):
                return hash(self.value)
            def __eq__(self, other):
                if other == self.value:
                    return True
                return False

        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        assert not s1.has_key(self.space.wrap("five"))
        skip("currently not supported")
        assert s1.strategy is self.space.fromcache(IntegerSetStrategy)

        assert s1.has_key(self.space.wrap(FakeInt(2)))
        assert s1.strategy is self.space.fromcache(ObjectSetStrategy)

    def test_iter(self):
        space = self.space
        s = W_SetObject(space, self.wrapped([1,2]))
        it = s.iter()
        assert isinstance(it, IntegerIteratorImplementation)
        assert space.unwrap(it.next()) == 1
        assert space.unwrap(it.next()) == 2
        #
        s = W_SetObject(space, self.wrapped(["a", "b"]))
        it = s.iter()
        assert isinstance(it, BytesIteratorImplementation)
        assert space.unwrap(it.next()) == "a"
        assert space.unwrap(it.next()) == "b"
        #
        s = W_SetObject(space, self.wrapped([u"a", u"b"]))
        it = s.iter()
        assert isinstance(it, UnicodeIteratorImplementation)
        assert space.unwrap(it.next()) == u"a"
        assert space.unwrap(it.next()) == u"b"

    def test_listview(self):
        space = self.space
        s = W_SetObject(space, self.wrapped([1,2]))
        assert sorted(space.listview_int(s)) == [1, 2]
        #
        s = W_SetObject(space, self.wrapped(["a", "b"]))
        assert sorted(space.listview_bytes(s)) == ["a", "b"]
        #
        s = W_SetObject(space, self.wrapped([u"a", u"b"]))
        assert sorted(space.listview_unicode(s)) == [u"a", u"b"]


class TestSetHypothesis:
    def wrapped(self, l):
        return W_ListObject(self.space, [self.space.wrap(x) for x in l])

    def wrap(self, x):
        return self.space.wrap(x)

    def intset(self, content):
        return W_SetObject(self.space, self.wrapped(content))

    @given(intlists, ints)
    def test_intset_added_element_in_set(self, content, i):
        s = self.intset(content)
        w_i = self.wrap(i)
        s.add(w_i)
        assert s.has_key(w_i)

    @given(intlists, ints)
    def test_remove(self, content, i):
        s = self.intset(content + [i])
        w_i = self.wrap(i)
        s.remove(w_i)
        assert not s.has_key(w_i)

    @given(intlists, ints)
    def test_length(self, content, i):
        s = self.intset(content)
        assert len(set(content)) == s.length()

    @given(intlists, intlists)
    def test_update(self, c1, c2):
        s1 = self.intset(c1)
        s2 = self.intset(c2)
        s1.update(s2)
        for i in c1:
            assert s1.has_key(self.wrap(i))
        for i in c2:
            assert s1.has_key(self.wrap(i))
        # XXX check that no additional keys

    @given(intlists, intlists)
    def test_symmetric_update(self, c1, c2):
        s1 = self.intset(c1)
        s2 = self.intset(c2)
        s1.symmetric_difference_update(s2)
        s1.length()
        for i in c1:
            if i not in c2:
                assert s1.has_key(self.wrap(i))
            else:
                assert not s1.has_key(self.wrap(i))
        for i in c2:
            if i not in c1:
                assert s1.has_key(self.wrap(i))
            else:
                assert not s1.has_key(self.wrap(i))
        # XXX check that no additional keys

    @given(intlists, intlists)
    def test_difference_update(self, c1, c2):
        s1 = self.intset(c1)
        s2 = self.intset(c2)
        s1.difference_update(s2)
        s1.length()
        for i in c1:
            if i not in c2:
                assert s1.has_key(self.wrap(i))
            else:
                assert not s1.has_key(self.wrap(i))
        for i in c2:
            assert not s1.has_key(self.wrap(i))
        # XXX check that no additional keys

    @given(intlists, intlists)
    def XXXtest_update_vs_not(self, c1, c2):
        return #XXX write me!

    @given(intlists, intlists)
    def test_intersect(self, c1, c2):
        s1 = self.intset(c1)
        s2 = self.intset(c2)
        s = s1.intersect(s2)
        for i in c1:
            if i in c2:
                assert s.has_key(self.wrap(i))
            else:
                assert not s.has_key(self.wrap(i))
        for i in c2:
            if i in c1:
                assert s.has_key(self.wrap(i))
            else:
                assert not s.has_key(self.wrap(i))
        # XXX check that no additional keys


    @given(intlists, intlists)
    def test_issubset(self, c1, c2):
        s1 = self.intset(c1)
        s2 = self.intset(c1)
        for i in c2:
            s2.remove(self.wrap(i))
        assert s2.issubset(s1)
        assert not s1.issubset(s2) or s1.equals(s2)
