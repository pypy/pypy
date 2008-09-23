"""
The main test for the set implementation is located
at:
    pypy-dist/lib-python/modified-2.4.1/test/test_set.py
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
