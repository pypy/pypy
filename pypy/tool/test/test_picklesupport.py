from pypy.tool.picklesupport import *

import pickle
import py

class A(object):
    __slots__ = ("a", "b")
    __getstate__ = getstate_with_slots
    __setstate__ = setstate_with_slots

class B(A):
    __slots__ = ("c", "d")

class C(B):
    pass

def test_slot_getstate_setstate():
    b = B()
    b.a, b.c = range(2)
    s = pickle.dumps(b)
    new_b = pickle.loads(s)
    assert new_b.a == b.a
    py.test.raises(AttributeError, "new_b.b")
    assert new_b.c == b.c
    py.test.raises(AttributeError, "new_b.d")

def test_slot_getstate_setstate_with_dict():
    c = C()
    assert '__dict__' in dir(c)
    c.a, c.b, c.c, c.d, c.e = range(5)
    s = pickle.dumps(c)
    new_c = pickle.loads(s)
    assert new_c.a == c.a
    assert new_c.b == c.b
    assert new_c.c == c.c
    assert new_c.d == c.d
    assert new_c.e == c.e

class D(B):
    __slots__ = '__weakref__'

def test_slot_getstate_setstate_with_weakref():
    d = D()
    s = pickle.dumps(d)
    new_d = pickle.loads(s)
    assert new_d.__weakref__ is None

def test_pickleable_weakref():
    d = D()
    ref = pickleable_weakref(d)
    s = pickle.dumps((d, ref))
    new_d, new_ref = pickle.loads(s)
    assert new_ref() is new_d   
    del new_d
    assert new_ref() is None

def test_pickleable_weakref_dieing():
    d = D()
    ref = pickleable_weakref(d)
    s = pickle.dumps(ref)
    new_ref = pickle.loads(s)
    assert new_ref() is None

class E(B):
    __slots__ = ()
    def __init__(self, a, b, c, d):
        self.__class__.a.__set__(self, a)
        self.__class__.b.__set__(self, b)
        self.__class__.c.__set__(self, c)
        self.__class__.d.__set__(self, d)
    def __getattr__(self, attr):
        raise AttributeError("not found")

def test_getsetstate_getattr():
    e = E(1, 2, 3, 4)
    s = pickle.dumps(e)
    new_e = pickle.loads(s)
    assert new_e.a == 1
    assert new_e.b == 2
    assert new_e.c == 3
    assert new_e.d == 4

class F(B):
    __slots__ = "__dict__"
    def __init__(self, a, b, c, d, e):
        self.__class__.a.__set__(self, a)
        self.__class__.b.__set__(self, b)
        self.__class__.c.__set__(self, c)
        self.__class__.d.__set__(self, d)
        self.__dict__['e'] = e
    def __getattr__(self, attr):
        raise AttributeError("not found")
 
def test_getsetstate_getattr_withdict():
    f = F(1, 2, 3, 4, 5)
    assert '__dict__' in dir(f)
    s = pickle.dumps(f)
    new_f = pickle.loads(s)
    assert new_f.a == 1
    assert new_f.b == 2
    assert new_f.c == 3
    assert new_f.d == 4
    assert new_f.e == 5

