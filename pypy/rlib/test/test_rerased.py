import py
import sys
from pypy.rlib.rerased import *
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rpython.ootypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype, llmemory

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

class X(object):
    pass

class Y(X):
    pass

class Z(X):
    pass

eraseX, uneraseX = new_erasing_pair("X")
erase_list_X, unerase_list_X = new_erasing_pair("list of X")


def test_simple():
    x1 = X()
    e = eraseX(x1)
    #assert is_integer(e) is False
    assert uneraseX(e) is x1

def test_simple_none():
    e = eraseX(None)
    assert uneraseX(e) is None

def test_simple_int():
    e = erase_int(15)
    #assert is_integer(e) is True
    assert unerase_int(e) == 15

def test_simple_int_overflow():
    erase_int(sys.maxint//2)
    py.test.raises(OverflowError, erase_int, sys.maxint//2 + 1)
    py.test.raises(OverflowError, erase_int, sys.maxint)
    py.test.raises(OverflowError, erase_int, sys.maxint-1)
    py.test.raises(OverflowError, erase_int, -sys.maxint)
    py.test.raises(OverflowError, erase_int, -sys.maxint-1)

def test_list():
    l = [X()]
    e = erase_list_X(l)
    #assert is_integer(e) is False
    assert unerase_list_X(e) is l

def test_annotate_1():
    def f():
        return eraseX(X())
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, SomeErased)

def test_annotate_2():
    def f():
        x1 = X()
        e = eraseX(x1)
        #assert not is_integer(e)
        x2 = uneraseX(e)
        return x2
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInstance)
    assert s.classdef == a.bookkeeper.getuniqueclassdef(X)

def test_annotate_3():
    def f():
        e = erase_int(16)
        #assert is_integer(e)
        x2 = unerase_int(e)
        return x2
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInteger)

def test_annotate_erasing_pair():
    erase, unerase = new_erasing_pair("test1")
    erase2, unerase2 = new_erasing_pair("test2")
    class Foo:
        pass
    #
    def make(n):
        if n > 5:
            return erase([5, 6, n-6])
        else:
            foo = Foo()
            foo.bar = n+1
            return erase2(foo)

    def check(x, n):
        if n > 5:
            return unerase(x)[2]
        else:
            return unerase2(x).bar

    def f(n):
        x = make(n)
        return check(x, n)
    #
    a = RPythonAnnotator()
    s = a.build_types(f, [int])
    assert isinstance(s, annmodel.SomeInteger)

def test_annotate_reflowing():
    erase, unerase = new_erasing_pair("test1")
    class A: pass
    class B(A): pass
    class C(B): pass
    class D(C): pass

    def f():
        x = erase(None)
        while True:
            inst = unerase(x)
            if inst is None:
                inst = D()
                x = erase(inst)
            elif isinstance(inst, D):
                inst = C()
                x = erase(inst)
            elif isinstance(inst, C):
                inst = B()
                x = erase(inst)
            elif isinstance(inst, B):
                inst = A()
                x = erase(inst)
            else:
                return inst
    #
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInstance)
    assert s.classdef == a.bookkeeper.getuniqueclassdef(A)

def test_annotate_prebuilt():
    erase, unerase = new_erasing_pair("test1")
    class X(object):
        pass
    x1 = X()
    e1 = erase(x1)
    e2 = erase(None)

    def f(i):
        if i:
            e = e1
        else:
            e = e2
        return unerase(e)
    #
    a = RPythonAnnotator()
    s = a.build_types(f, [int])
    assert isinstance(s, annmodel.SomeInstance)
    assert s.classdef == a.bookkeeper.getuniqueclassdef(X)
    assert s.can_be_none()

def test_annotate_prebuilt_int():
    e1 = erase_int(42)
    def f(i):
        return unerase_int(e1)
    a = RPythonAnnotator()
    s = a.build_types(f, [int])
    assert isinstance(s, annmodel.SomeInteger)

class BaseTestRErased(BaseRtypingTest):
    def test_rtype_1(self):
        def f():
            return eraseX(X())
        x = self.interpret(f, [])
        assert lltype.typeOf(x) == self.ERASED_TYPE

    def test_rtype_2(self):
        def f():
            x1 = X()
            e = eraseX(x1)
            #assert not is_integer(e)
            x2 = uneraseX(e)
            return x2
        x = self.interpret(f, [])
        assert self.castable(self.UNERASED_TYPE, x)

    def test_rtype_3(self):
        def f():
            e = erase_int(16)
            #assert is_integer(e)
            x2 = unerase_int(e)
            return x2
        x = self.interpret(f, [])
        assert x == 16

    def test_prebuilt_erased(self):
        e1 = erase_int(16)
        x1 = X()
        x1.foobar = 42
        e2 = eraseX(x1)

        def f():
            #assert is_integer(e1)
            #assert not is_integer(e2)
            x1.foobar += 1
            x2 = unerase_int(e1) + uneraseX(e2).foobar
            return x2
        x = self.interpret(f, [])
        assert x == 16 + 42 + 1

    def test_prebuilt_erased_in_instance(self):
        erase_empty, unerase_empty = new_erasing_pair("empty")
        class FakeList(object):
            pass

        x1 = X()
        x1.foobar = 42
        l1 = FakeList()
        l1.storage = eraseX(x1)
        l2 = FakeList()
        l2.storage = erase_empty(None)

        def f():
            #assert is_integer(e1)
            #assert not is_integer(e2)
            x1.foobar += 1
            x2 = uneraseX(l1.storage).foobar + (unerase_empty(l2.storage) is None)
            return x2
        x = self.interpret(f, [])
        assert x == 43 + True

    def test_overflow(self):
        def f(i):
            try:
                e = erase_int(i)
            except OverflowError:
                return -1
            #assert is_integer(e)
            return unerase_int(e)
        x = self.interpret(f, [16])
        assert x == 16
        x = self.interpret(f, [sys.maxint])
        assert x == -1

    def test_none(self):
        def foo():
            return uneraseX(eraseX(None))
        assert foo() is None
        res = self.interpret(foo, [])
        assert not res
        #
        def foo():
            eraseX(X())
            return uneraseX(eraseX(None))
        assert foo() is None
        res = self.interpret(foo, [])
        assert not res

    def test_rtype_list(self):
        prebuilt_l = [X()]
        prebuilt_e = erase_list_X(prebuilt_l)
        def l(flag):
            if flag == 1:
                l = [X()]
                e = erase_list_X(l)
            elif flag == 2:
                l = prebuilt_l
                e = erase_list_X(l)
            else:
                l = prebuilt_l
                e = prebuilt_e
            #assert is_integer(e) is False
            assert unerase_list_X(e) is l
        self.interpret(l, [0])
        self.interpret(l, [1])
        self.interpret(l, [2])

class TestLLtype(BaseTestRErased, LLRtypeMixin):
    ERASED_TYPE = llmemory.GCREF
    UNERASED_TYPE = OBJECTPTR
    def castable(self, TO, var):
        return lltype.castable(TO, lltype.typeOf(var)) > 0

class TestOOtype(BaseTestRErased, OORtypeMixin):
    ERASED_TYPE = Object
    UNERASED_TYPE = OBJECT
    def castable(self, TO, var):
        return ootype.isSubclass(lltype.typeOf(var), TO)

def test_union():
    s_e1 = SomeErased()
    s_e1.const = 1
    s_e2 = SomeErased()
    s_e2.const = 3
    assert not annmodel.pair(s_e1, s_e2).union().is_constant()

# ____________________________________________________________

def test_erasing_pair():
    erase, unerase = new_erasing_pair("test1")
    class X:
        pass
    x = X()
    erased = erase(x)
    assert unerase(erased) is x
    #
    erase2, unerase2 = new_erasing_pair("test2")
    py.test.raises(AssertionError, unerase2, erased)
