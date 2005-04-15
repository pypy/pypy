
import autopath
from pypy.annotation.model import *
from pypy.annotation.listdef import ListDef, MOST_GENERAL_LISTDEF


listdef1 = ListDef(None, SomeTuple([SomeInteger(nonneg=True), SomeString()]))
listdef2 = ListDef(None, SomeTuple([SomeInteger(nonneg=False), SomeString()]))

s1 = SomeObject()
s2 = SomeInteger(nonneg=True)
s3 = SomeInteger(nonneg=False)
s4 = SomeList(listdef1)
s5 = SomeList(listdef2)
s6 = SomeImpossibleValue()
slist = [s1,s2,s3,s4,s6]  # not s5 -- unionof(s4,s5) modifies s4 and s5


class C(object):
    pass

class DummyClassDef:
    def __init__(self, cls=C):
        self.cls = cls

si0 = SomeInstance(DummyClassDef(), True)
si1 = SomeInstance(DummyClassDef())
sNone = SomePBC({None: True})
sTrue = SomeBool()
sTrue.const = True
sFalse = SomeBool()
sFalse.const = False

def test_is_None():
    assert pair(sNone, sNone).is_() == sTrue
    assert pair(si1, sNone).is_() == sFalse
    assert pair(si0, sNone).is_() != sTrue
    assert pair(si0, sNone).is_() != sFalse
    assert pair(si0, sNone).is_() == SomeBool()

def test_equality():
    assert s1 != s2 != s3 != s4 != s5 != s6
    assert s1 == SomeObject()
    assert s2 == SomeInteger(nonneg=True)
    assert s3 == SomeInteger(nonneg=False)
    assert s4 == SomeList(listdef1)
    assert s5 == SomeList(listdef2)
    assert s6 == SomeImpossibleValue()

def test_contains():
    assert ([(s,t) for s in slist for t in slist if s.contains(t)] ==
            [(s1,s1), (s1,s2), (s1,s3), (s1,s4), (s1,s6),
                      (s2,s2),                   (s2,s6),
                      (s3,s2), (s3,s3),          (s3,s6),
                                        (s4,s4), (s4,s6),
                                                 (s6,s6)])

def test_union():
    assert ([unionof(s,t) for s in slist for t in slist] ==
            [s1, s1, s1, s1, s1,
             s1, s2, s3, s1, s2,
             s1, s3, s3, s1, s3,
             s1, s1, s1, s4, s4,
             s1, s2, s3, s4, s6])

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
    class B3(object, A0):
        pass
    assert commonbase(A1,A2) is A0 
    assert commonbase(A1,A0) is A0
    assert commonbase(A1,A1) is A1
    assert commonbase(A2,B2) is object 
    assert commonbase(A2,B3) is A0

def test_list_union():
    listdef1 = ListDef(None, SomeInteger(nonneg=True))
    listdef2 = ListDef(None, SomeInteger(nonneg=False))
    s1 = SomeList(listdef1)
    s2 = SomeList(listdef2)
    assert s1 != s2
    s3 = unionof(s1, s2)
    assert s1 == s2 == s3

def test_list_contains():
    listdef1 = ListDef(None, SomeInteger(nonneg=True))
    s1 = SomeList(listdef1)
    s2 = SomeList(MOST_GENERAL_LISTDEF)
    assert s1 != s2
    assert s2.contains(s1)
    assert s1 != s2
    assert not s1.contains(s2)
    assert s1 != s2

if __name__ == '__main__':
    for name, value in globals().items():
        if name.startswith('test_'):
            value()
