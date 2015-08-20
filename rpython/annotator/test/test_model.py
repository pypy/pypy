import py

from rpython.annotator.model import *
from rpython.annotator.listdef import ListDef
from rpython.translator.translator import TranslationContext


listdef1 = ListDef(None, SomeTuple([SomeInteger(nonneg=True), SomeString()]))
listdef2 = ListDef(None, SomeTuple([SomeInteger(nonneg=False), SomeString()]))

s1 = SomeType()
s2 = SomeInteger(nonneg=True)
s3 = SomeInteger(nonneg=False)
s4 = SomeList(listdef1)
s5 = SomeList(listdef2)
s6 = SomeImpossibleValue()
slist = [s1, s2, s3, s4, s6]  # not s5 -- unionof(s4,s5) modifies s4 and s5


class C(object):
    pass

def test_equality():
    assert s1 != s2 != s3 != s4 != s5 != s6
    assert s1 == SomeType()
    assert s2 == SomeInteger(nonneg=True)
    assert s3 == SomeInteger(nonneg=False)
    assert s4 == SomeList(listdef1)
    assert s5 == SomeList(listdef2)
    assert s6 == SomeImpossibleValue()

def test_contains():
    assert ([(s,t) for s in slist for t in slist if s.contains(t)] ==
            [(s1, s1),                               (s1, s6),
                       (s2, s2),                     (s2, s6),
                       (s3, s2), (s3, s3),           (s3, s6),
                                           (s4, s4), (s4, s6),
                                                     (s6, s6)])

def test_signedness():
    assert not SomeInteger(unsigned=True).contains(SomeInteger())
    assert SomeInteger(unsigned=True).contains(SomeInteger(nonneg=True))

def test_commonbase_simple():
    class A0:
        pass
    class A1(A0):
        pass
    class A2(A0):
        pass
    class B1(object):
        pass
    class B2(object):
        pass
    try:
        class B3(object, A0):
            pass
    except TypeError:    # if A0 is also a new-style class, e.g. in PyPy
        class B3(A0, object):
            pass
    assert commonbase(A1,A2) is A0
    assert commonbase(A1,A0) is A0
    assert commonbase(A1,A1) is A1
    assert commonbase(A2,B2) is object
    assert commonbase(A2,B3) is A0

def test_list_union():
    listdef1 = ListDef('dummy', SomeInteger(nonneg=True))
    listdef2 = ListDef('dummy', SomeInteger(nonneg=False))
    s1 = SomeList(listdef1)
    s2 = SomeList(listdef2)
    assert s1 != s2
    s3 = unionof(s1, s2)
    assert s1 == s2 == s3

def test_list_contains():
    listdef1 = ListDef(None, SomeInteger(nonneg=True))
    s1 = SomeList(listdef1)
    listdef2 = ListDef(None, SomeInteger(nonneg=False))
    s2 = SomeList(listdef2)
    assert s1 != s2
    assert not s2.contains(s1)
    assert s1 != s2
    assert not s1.contains(s2)
    assert s1 != s2

def test_nan():
    f1 = SomeFloat()
    f1.const = float("nan")
    f2 = SomeFloat()
    f2.const = float("nan")
    assert f1.contains(f1)
    assert f2.contains(f1)
    assert f1.contains(f2)

def compile_function(function, annotation=[]):
    t = TranslationContext()
    t.buildannotator().build_types(function, annotation)

class AAA(object):
    pass

def test_blocked_inference1():
    def blocked_inference():
        return AAA().m()

    py.test.raises(AnnotatorError, compile_function, blocked_inference)

def test_blocked_inference2():
    def blocked_inference():
        a = AAA()
        b = a.x
        return b

    py.test.raises(AnnotatorError, compile_function, blocked_inference)


def test_not_const():
    s_int = SomeInteger()
    s_int.const = 2
    assert s_int != SomeInteger()
    assert not_const(s_int) == SomeInteger()
    assert not_const(s_None) == s_None


def test_nonnulify():
    s = SomeString(can_be_None=True).nonnulify()
    assert s.can_be_None is True
    assert s.no_nul is True
    s = SomeChar().nonnulify()
    assert s.no_nul is True
