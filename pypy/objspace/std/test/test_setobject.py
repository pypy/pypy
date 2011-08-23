"""
The main test for the set implementation is located
at:
    pypy-dist/lib-python/modified-2.5.2/test/test_set.py
    go there and invoke
    ../../../pypy/bin/py.py test_set.py
This file just contains some basic tests that make sure, the implementation
is not too wrong.
"""
import py.test
from pypy.objspace.std.setobject import W_SetObject, W_FrozensetObject
from pypy.objspace.std.setobject import _initialize_set
from pypy.objspace.std.setobject import newset
from pypy.objspace.std.setobject import and__Set_Set
from pypy.objspace.std.setobject import set_intersection__Set
from pypy.objspace.std.setobject import eq__Set_Set
from pypy.conftest import gettestobjspace

letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

class W_SubSetObject(W_SetObject):pass

class TestW_SetObject:

    def setup_method(self, method):
        self.word = self.space.wrap('simsalabim')
        self.otherword = self.space.wrap('madagascar')
        self.letters = self.space.wrap(letters)
        self.true = self.space.w_True
        self.false = self.space.w_False

    def test_and(self):
        s = W_SetObject(self.space)
        _initialize_set(self.space, s, self.word)
        t0 = W_SetObject(self.space)
        _initialize_set(self.space, t0, self.otherword)
        t1 = W_FrozensetObject(self.space, self.otherword)
        r0 = and__Set_Set(self.space, s, t0)
        r1 = and__Set_Set(self.space, s, t1)
        assert eq__Set_Set(self.space, r0, r1) == self.true
        sr = set_intersection__Set(self.space, s, [self.otherword])
        assert eq__Set_Set(self.space, r0, sr) == self.true

    def test_compare(self):
        s = W_SetObject(self.space)
        _initialize_set(self.space, s, self.word)
        t = W_SetObject(self.space)
        _initialize_set(self.space, t, self.word)
        assert self.space.eq_w(s,t)
        u = self.space.wrap(set('simsalabim'))
        assert self.space.eq_w(s,u)

    def test_space_newset(self):
        s = self.space.newset()
        assert self.space.str_w(self.space.repr(s)) == 'set([])'

class AppTestAppSetTest:

    def setup_class(self):
        self.space = gettestobjspace()
        w_fakeint = self.space.appexec([], """():
            class FakeInt(object):
                def __init__(self, value):
                    self.value = value
                def __hash__(self):
                    return hash(self.value)

                def __eq__(self, other):
                    if other == self.value:
                        return True
                    return False
            return FakeInt
            """)
        self.w_FakeInt = w_fakeint

    def test_fakeint(self):
        f1 = self.FakeInt(4)
        assert f1 == 4
        assert hash(f1) == hash(4)

    def test_simple(self):
        a = set([1,2,3])
        b = set()
        b.add(4)
        c = a.union(b)
        assert c == set([1,2,3,4])

    def test_generator(self):
        def foo():
            for i in [1,2,3,4,5]:
                yield i
        b = set(foo())
        assert b == set([1,2,3,4,5])

        a = set(x for x in [1,2,3])
        assert a == set([1,2,3])

    def test_generator2(self):
        def foo():
            for i in [1,2,3]:
                yield i
        class A(set):
            pass
        a = A([1,2,3,4,5])
        b = a.difference(foo())
        assert b == set([4,5])

    def test_or(self):
        a = set([0,1,2])
        b = a | set([1,2,3])
        assert b == set([0,1,2,3])

        # test inplace or
        a |= set([1,2,3])
        assert a == b

    def test_clear(self):
        a = set([1,2,3])
        a.clear()
        assert a == set()

    def test_sub(self):
        a = set([1,2,3,4,5])
        b = set([2,3,4])
        a - b == [1,5]
        a.__sub__(b) == [1,5]

        #inplace sub
        a = set([1,2,3,4])
        b = set([1,4])
        a -= b
        assert a == set([2,3])

    def test_issubset(self):
        a = set([1,2,3,4])
        b = set([2,3])
        assert b.issubset(a)
        c = [1,2,3,4]
        assert b.issubset(c)

    def test_issuperset(self):
        a = set([1,2,3,4])
        b = set([2,3])
        assert a.issuperset(b)
        c = [2,3]
        assert a.issuperset(c)

        c = [1,1,1,1,1]
        assert a.issuperset(c)
        assert set([1,1,1,1,1]).issubset(a)

    def test_inplace_and(test):
        a = set([1,2,3,4])
        b = set([0,2,3,5,6])
        a &= b
        assert a == set([2,3])

    def test_discard_remove(self):
        a = set([1,2,3,4,5])
        a.remove(1)
        assert a == set([2,3,4,5])
        a.discard(2)
        assert a == set([3,4,5])

        raises(KeyError, "a.remove(6)")

    def test_pop(self):
        b = set()
        raises(KeyError, "b.pop()")

        a = set([1,2,3,4,5])
        for i in xrange(5):
            a.pop()
        assert a == set()
        raises(KeyError, "a.pop()")

    def test_symmetric_difference(self):
        a = set([1,2,3])
        b = set([3,4,5])
        c = a.symmetric_difference(b)
        assert c == set([1,2,4,5])

        a = set([1,2,3])
        b = [3,4,5]
        c = a.symmetric_difference(b)
        assert c == set([1,2,4,5])

    def test_symmetric_difference_update(self):
        a = set([1,2,3])
        b = set([3,4,5])
        a.symmetric_difference_update(b)
        assert a == set([1,2,4,5])

        a = set([1,2,3])
        b = [3,4,5]
        a.symmetric_difference_update(b)
        assert a == set([1,2,4,5])

        a = set([1,2,3])
        b = set([3,4,5])
        a ^= b
        assert a == set([1,2,4,5])

    def test_subtype(self):
        class subset(set):pass
        a = subset()
        b = a | set('abc')
        assert type(b) is subset

    def test_init_new_behavior(self):
        s = set.__new__(set, 'abc')
        assert s == set()                # empty
        s.__init__('def')
        assert s == set('def')
        #
        s = frozenset.__new__(frozenset, 'abc')
        assert s == frozenset('abc')     # non-empty
        s.__init__('def')
        assert s == frozenset('abc')     # the __init__ is ignored

    def test_subtype_bug(self):
        class subset(set): pass
        b = subset('abc')
        subset.__new__ = lambda *args: foobar   # not called
        b = b.copy()
        assert type(b) is subset
        assert set(b) == set('abc')
        #
        class frozensubset(frozenset): pass
        b = frozensubset('abc')
        frozensubset.__new__ = lambda *args: foobar   # not called
        b = b.copy()
        assert type(b) is frozensubset
        assert frozenset(b) == frozenset('abc')

    def test_union(self):
        a = set([4, 5])
        b = a.union([5, 7])
        assert sorted(b) == [4, 5, 7]
        c = a.union([5, 7], [1], set([9,7]), frozenset([2]), frozenset())
        assert sorted(c) == [1, 2, 4, 5, 7, 9]
        d = a.union()
        assert d == a

    def test_compare(self):
        raises(TypeError, cmp, set('abc'), set('abd'))
        assert set('abc') != 'abc'
        raises(TypeError, "set('abc') < 42")
        assert not (set('abc') < set('def'))
        assert not (set('abc') <= frozenset('abd'))
        assert not (set('abc') < frozenset('abd'))
        assert not (set('abc') >= frozenset('abd'))
        assert not (set('abc') > frozenset('abd'))
        assert set('abc') <= frozenset('abc')
        assert set('abc') >= frozenset('abc')
        assert set('abc') <= frozenset('abcd')
        assert set('abc') >= frozenset('ab')
        assert set('abc') < frozenset('abcd')
        assert set('abc') > frozenset('ab')
        assert not (set('abc') < frozenset('abc'))
        assert not (set('abc') > frozenset('abc'))
        assert not set() == 42
        assert set() != 42
        assert (set('abc') == frozenset('abc'))
        assert (set('abc') == set('abc'))
        assert (frozenset('abc') == frozenset('abc'))
        assert (frozenset('abc') == set('abc'))
        assert not (set('abc') != frozenset('abc'))
        assert not (set('abc') != set('abc'))
        assert not (frozenset('abc') != frozenset('abc'))
        assert not (frozenset('abc') != set('abc'))
        assert not (set('abc') == frozenset('abcd'))
        assert not (set('abc') == set('abcd'))
        assert not (frozenset('abc') == frozenset('abcd'))
        assert not (frozenset('abc') == set('abcd'))
        assert (set('abc') != frozenset('abcd'))
        assert (set('abc') != set('abcd'))
        assert (frozenset('abc') != frozenset('abcd'))
        assert (frozenset('abc') != set('abcd'))

    def test_libpython_equality(self):
        for thetype in [frozenset, set]:
            word = "aaaaaaaaawfpasrtarspawparst"
            otherword = "ZZZZZZZXCVZXCVSRTD"
            s = thetype(word)
            assert s == set(word)
            assert s, frozenset(word)
            assert not s == word
            assert s != set(otherword)
            assert s != frozenset(otherword)
            assert s != word

    def test_copy(self):
        s1 = set('abc')
        s2 = s1.copy()
        assert s1 is not s2
        assert s1 == s2
        assert type(s2) is set
        s1 = frozenset('abc')
        s2 = s1.copy()
        assert s1 is s2
        assert s1 == s2
        class myfrozen(frozenset):
            pass
        s1 = myfrozen('abc')
        s2 = s1.copy()
        assert s1 is not s2
        assert s1 == s2
        assert type(s2) is myfrozen

    def test_update(self):
        s1 = set('abc')
        s1.update(set('abcd'))
        assert s1 == set('abcd')
        s1 = set('abc')
        s1.update(frozenset('fro'))
        assert s1 == set('abcfro')
        s1 = set('abc')
        s1.update('def')
        assert s1 == set('abcdef')
        s1 = set('abc')
        s1.update()
        assert s1 == set('abc')
        s1 = set('abc')
        s1.update('d', 'ef', frozenset('g'))
        assert s1 == set('abcdefg')

    def test_recursive_repr(self):
        class A(object):
            def __init__(self, s):
                self.s = s
            def __repr__(self):
                return repr(self.s)
        
        s = set([1, 2, 3])
        s.add(A(s))
        therepr = repr(s)
        assert therepr.startswith("set([")
        assert therepr.endswith("])")
        inner = set(therepr[5:-2].split(", "))
        assert inner == set(["1", "2", "3", "set(...)"])

    def test_recursive_repr_frozenset(self):
        class A(object):
            def __repr__(self):
                return repr(self.s)
        a = A()
        s = frozenset([1, 2, 3, a])
        a.s = s
        therepr = repr(s)
        assert therepr.startswith("frozenset([")
        assert therepr.endswith("])")
        inner = set(therepr[11:-2].split(", "))
        assert inner == set(["1", "2", "3", "frozenset(...)"])
        
    def test_keyerror_has_key(self):
        s = set()
        try:
            s.remove(1)
        except KeyError, e:
            assert e.args[0] == 1
        else:
            assert 0, "should raise"

    def test_subclass_with_hash(self):
        # Bug #1257731
        class H(set):
            def __hash__(self):
                return int(id(self) & 0x7fffffff)
        s = H()
        f = set([s])
        print f
        assert s in f
        f.remove(s)
        f.add(s)
        f.discard(s)

    def test_autoconvert_to_frozen__contains(self):
        s = set([frozenset([1,2])])

        assert set([1,2]) in s

    def test_autoconvert_to_frozen_remove(self):
        s = set([frozenset([1,2])])

        s.remove(set([1,2]))
        assert len(s) == 0
        raises(KeyError, s.remove, set([1,2]))

    def test_autoconvert_to_frozen_discard(self):
        s = set([frozenset([1,2])])

        s.discard(set([1,2]))
        assert len(s) == 0
        s.discard(set([1,2]))

    def test_autoconvert_to_frozen_onlyon_type_error(self):
        class A(set):
            def __hash__(self):
                return id(self)

        s = A([1, 2, 3])
        s2 = set([2, 3, s])
        assert A() not in s2
        s2.add(frozenset())
        assert A() not in s2
        raises(KeyError, s2.remove, A())

    def test_autoconvert_key_error(self):
        s = set([frozenset([1, 2]), frozenset([3, 4])])
        key = set([2, 3])
        try:
            s.remove(key)
        except KeyError, e:
            assert e.args[0] is key

    def test_contains(self):
        letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        word = 'teleledningsanka'
        s = set(word)
        for c in letters:
            assert (c in s) == (c in word)
        raises(TypeError, s.__contains__, [])

    def test_remove(self):
        s = set('abc')
        s.remove('a')
        assert 'a' not in s
        raises(KeyError, s.remove, 'a')
        raises(TypeError, s.remove, [])
        s.add(frozenset('def'))
        assert set('def') in s
        s.remove(set('def'))
        assert set('def') not in s
        raises(KeyError, s.remove, set('def'))

    def test_remove_keyerror_unpacking(self):
        # bug:  www.python.org/sf/1576657
        s = set()
        for v1 in ['Q', (1,)]:
            try:
                s.remove(v1)
            except KeyError, e:
                v2 = e.args[0]
                assert v1 == v2
            else:
                assert False, 'Expected KeyError'
        
    def test_singleton_empty_frozenset(self):
        class Frozenset(frozenset):
            pass
        f = frozenset()
        F = Frozenset()
        efs = [f, Frozenset(f)]
        # All empty frozenset subclass instances should have different ids
        assert len(set(map(id, efs))) == len(efs)

    def test_subclass_union(self):
        for base in [set, frozenset]:
            class subset(base):
                def __init__(self, *args):
                    self.x = args
            s = subset([2])
            assert s.x == ([2],)
            t = s | base([5])
            # obscure CPython behavior:
            assert type(t) is subset
            assert not hasattr(t, 'x')

    def test_isdisjoint(self):
        assert set([1,2,3]).isdisjoint(set([4,5,6]))
        assert set([1,2,3]).isdisjoint(frozenset([4,5,6]))
        assert set([1,2,3]).isdisjoint([4,5,6])
        assert set([1,2,3]).isdisjoint((4,5,6))
        assert not set([1,2,5]).isdisjoint(set([4,5,6]))
        assert not set([1,2,5]).isdisjoint(frozenset([4,5,6]))
        assert not set([1,2,5]).isdisjoint([4,5,6])
        assert not set([1,2,5]).isdisjoint((4,5,6))

    def test_intersection(self):
        assert set([1,2,3]).intersection(set([2,3,4])) == set([2,3])
        assert set([1,2,3]).intersection(frozenset([2,3,4])) == set([2,3])
        assert set([1,2,3]).intersection([2,3,4]) == set([2,3])
        assert set([1,2,3]).intersection((2,3,4)) == set([2,3])
        assert frozenset([1,2,3]).intersection(set([2,3,4])) == frozenset([2,3])
        assert frozenset([1,2,3]).intersection(frozenset([2,3,4]))== frozenset([2,3])
        assert frozenset([1,2,3]).intersection([2,3,4]) == frozenset([2,3])
        assert frozenset([1,2,3]).intersection((2,3,4)) == frozenset([2,3])
        assert set([1,2,3,4]).intersection([2,3,4,5], set((1,2,3))) == set([2,3])
        assert frozenset([1,2,3,4]).intersection((2,3,4,5), [1,2,3]) == \
                   frozenset([2,3])
        s = set([1,2,3])
        assert s.intersection() == s
        assert s.intersection() is not s

    def test_difference(self):
        assert set([1,2,3]).difference(set([2,3,4])) == set([1])
        assert set([1,2,3]).difference(frozenset([2,3,4])) == set([1])
        assert set([1,2,3]).difference([2,3,4]) == set([1])
        assert set([1,2,3]).difference((2,3,4)) == set([1])
        assert frozenset([1,2,3]).difference(set([2,3,4])) == frozenset([1])
        assert frozenset([1,2,3]).difference(frozenset([2,3,4]))== frozenset([1])
        assert frozenset([1,2,3]).difference([2,3,4]) == frozenset([1])
        assert frozenset([1,2,3]).difference((2,3,4)) == frozenset([1])
        assert set([1,2,3,4]).difference([4,5], set((0,1))) == set([2,3])
        assert frozenset([1,2,3,4]).difference((4,5), [0,1]) == frozenset([2,3])
        s = set([1,2,3])
        assert s.difference() == s
        assert s.difference() is not s
        assert set([1,2,3]).difference(set([2,3,4,'5'])) == set([1])
        assert set([1,2,3,'5']).difference(set([2,3,4])) == set([1,'5'])

    def test_intersection_update(self):
        s = set([1,2,3,4,7])
        s.intersection_update([0,1,2,3,4,5,6])
        assert s == set([1,2,3,4])
        s.intersection_update((2,3,4,5), frozenset([0,1,2,3]))
        assert s == set([2,3])
        s.intersection_update()
        assert s == set([2,3])

    def test_difference_update(self):
        s = set([1,2,3,4,7])
        s.difference_update([0,7,8,9])
        assert s == set([1,2,3,4])
        s.difference_update((0,1), frozenset([4,5,6]))
        assert s == set([2,3])
        s.difference_update()
        assert s == set([2,3])
        s.difference_update(s)
        assert s == set([])

    def test_empty_empty(self):
        assert set() == set([])

    def test_empty_difference(self):
        e = set()
        x = set([1,2,3])
        assert e.difference(x) == set()
        assert x.difference(e) == x

        e.difference_update(x)
        assert e == set()
        x.difference_update(e)
        assert x == set([1,2,3])

        assert e.symmetric_difference(x) == x
        assert x.symmetric_difference(e) == x

        e.symmetric_difference_update(e)
        assert e == e
        e.symmetric_difference_update(x)
        assert e == x

        x.symmetric_difference_update(set())
        assert x == set([1,2,3])

    def test_empty_intersect(self):
        e = set()
        x = set([1,2,3])
        assert e.intersection(x) == e
        assert x.intersection(e) == e
        assert e & x == e
        assert x & e == e

        e.intersection_update(x)
        assert e == set()
        e &= x
        assert e == set()
        x.intersection_update(e)
        assert x == set()

    def test_empty_issuper(self):
        e = set()
        x = set([1,2,3])
        assert e.issuperset(e) == True
        assert e.issuperset(x) == False
        assert x.issuperset(e) == True

        assert e.issuperset(set())
        assert e.issuperset([])

    def test_empty_issubset(self):
        e = set()
        x = set([1,2,3])
        assert e.issubset(e) == True
        assert e.issubset(x) == True
        assert x.issubset(e) == False
        assert e.issubset([])

    def test_empty_isdisjoint(self):
        e = set()
        x = set([1,2,3])
        assert e.isdisjoint(e) == True
        assert e.isdisjoint(x) == True
        assert x.isdisjoint(e) == True

    def test_empty_typeerror(self):
        s = set()
        raises(TypeError, s.difference, [[]])
        raises(TypeError, s.difference_update, [[]])
        raises(TypeError, s.intersection, [[]])
        raises(TypeError, s.intersection_update, [[]])
        raises(TypeError, s.symmetric_difference, [[]])
        raises(TypeError, s.symmetric_difference_update, [[]])
        raises(TypeError, s.update, [[]])

    def test_super_with_generator(self):
        def foo():
            for i in [1,2,3]:
                yield i
        set([1,2,3,4,5]).issuperset(foo())

    def test_isdisjoint_with_generator(self):
        def foo():
            for i in [1,2,3]:
                yield i
        set([1,2,3,4,5]).isdisjoint(foo())

    def test_fakeint_and_equals(self):
        s1 = set([1,2,3,4])
        s2 = set([1,2,self.FakeInt(3), 4])
        assert s1 == s2

    def test_fakeint_and_discard(self):
        # test with object strategy
        s = set([1, 2, 'three', 'four'])
        s.discard(self.FakeInt(2))
        assert s == set([1, 'three', 'four'])

        s.remove(self.FakeInt(1))
        assert s == set(['three', 'four'])
        raises(KeyError, s.remove, self.FakeInt(16))

        # test with int strategy
        s = set([1,2,3,4])
        s.discard(self.FakeInt(4))
        assert s == set([1,2,3])
        s.remove(self.FakeInt(3))
        assert s == set([1,2])
        raises(KeyError, s.remove, self.FakeInt(16))

    def test_fakeobject_and_has_key(self):
        s = set([1,2,3,4,5])
        assert 5 in s
        assert self.FakeInt(5) in s

    def test_fakeobject_and_pop(self):
        s = set([1,2,3,self.FakeInt(4),5])
        assert s.pop()
        assert s.pop()
        assert s.pop()
        assert s.pop()
        assert s.pop()
        assert s == set([])

    def test_fakeobject_and_difference(self):
        s = set([1,2,'3',4])
        s.difference_update([self.FakeInt(1), self.FakeInt(2)])
        assert s == set(['3',4])

        s = set([1,2,3,4])
        s.difference_update([self.FakeInt(1), self.FakeInt(2)])
        assert s == set([3,4])

    def test_frozenset_behavior(self):
        s = set([1,2,3,frozenset([4])])
        raises(TypeError, s.difference_update, [1,2,3,set([4])])

        s = set([1,2,3,frozenset([4])])
        s.discard(set([4]))
        assert s == set([1,2,3])

    def test_discard_unhashable(self):
        s = set([1,2,3,4])
        raises(TypeError, s.discard, [1])

    def test_discard_evil_compare(self):
        class Evil(object):
            def __init__(self, value):
                self.value = value
            def __hash__(self):
                return hash(self.value)
            def __eq__(self, other):
                if isinstance(other, frozenset):
                    raise TypeError
                if other == self.value:
                    return True
                return False
        s = set([1,2, Evil(frozenset([1]))])
        raises(TypeError, s.discard, set([1]))

    def test_create_set_from_set(self):
        x = set([1,2,3])
        y = set(x)
        x.pop()
        assert x == set([2,3])
        assert y == set([1,2,3])
