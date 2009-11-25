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
from pypy.objspace.std.setobject import set_intersection__Set_Set
from pypy.objspace.std.setobject import set_intersection__Set_ANY
from pypy.objspace.std.setobject import eq__Set_Set

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
        s = W_SetObject(self.space, None)
        _initialize_set(self.space, s, self.word)
        t0 = W_SetObject(self.space, None)
        _initialize_set(self.space, t0, self.otherword)
        t1 = W_FrozensetObject(self.space, None)
        _initialize_set(self.space, t1, self.otherword)
        r0 = set_intersection__Set_Set(self.space, s, t0)
        r1 = set_intersection__Set_Set(self.space, s, t1)
        assert eq__Set_Set(self.space, r0, r1) == self.true
        sr = set_intersection__Set_ANY(self.space, s, self.otherword)
        assert eq__Set_Set(self.space, r0, sr) == self.true

    def test_compare(self):
        s = W_SetObject(self.space, None)
        _initialize_set(self.space, s, self.word)
        t = W_SetObject(self.space, None)
        _initialize_set(self.space, t, self.word)
        assert self.space.eq_w(s,t)

class AppTestAppSetTest:
    def test_subtype(self):
        class subset(set):pass
        a = subset()
        b = a | set('abc')
        assert type(b) is subset

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
        class myfrozen(frozenset):
            def __new__(cls):
                return frozenset.__new__(cls, 'abc')
        s1 = myfrozen()
        raises(TypeError, s1.copy)

    def test_update(self):
        s1 = set('abc')
        s1.update(set('abcd'))
        assert s1 == set('abcd')
        s1 = set('abc')
        s1.update(frozenset('fro'))
        assert s1 == set('abcfro')

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
        try:
            s.remove(set([2, 3]))
        except KeyError, e:
            assert isinstance(e.args[0], frozenset)
            assert e.args[0] == frozenset([2, 3])

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
