
import autopath
from pypy.annotation.model import *


s1 = SomeObject()
s2 = SomeInteger(nonneg=True)
s3 = SomeInteger(nonneg=False)
s4 = SomeList({}, SomeTuple([SomeInteger(nonneg=True), SomeString()]))
s5 = SomeList({}, SomeTuple([SomeInteger(nonneg=False), SomeString()]))
s6 = SomeImpossibleValue()
s7 = SomeInteger(nonneg=True)
s7.const = 7
slist = [s1,s2,s3,s4,s5,s6, s7]

def test_equality():
    assert s1 != s2 != s3 != s4 != s5 != s6 != s7
    assert s1 == SomeObject()
    assert s2 == SomeInteger(nonneg=True)
    assert s3 == SomeInteger(nonneg=False)
    assert s4 == SomeList({}, SomeTuple([SomeInteger(nonneg=True), SomeString()]))
    assert s5 == SomeList({}, SomeTuple([SomeInteger(nonneg=False), SomeString()]))
    assert s6 == SomeImpossibleValue()


def test_contains():
    assert ([(s,t) for s in slist for t in slist if s.contains(t)] ==
            [(s1,s1), (s1,s2), (s1,s3), (s1,s4), (s1,s5), (s1,s6), (s1,s7),
                      (s2,s2),                            (s2,s6), (s2,s7),
                      (s3,s2), (s3,s3),                   (s3,s6), (s3,s7),
                                        (s4,s4),          (s4,s6),
                                        (s5,s4), (s5,s5), (s5,s6),
                                                          (s6,s6),
                                                          (s7,s6), (s7,s7)])

             
def test_contains_more():
    from pypy.annotation import bookkeeper
    bk = bookkeeper.Bookkeeper(None)
    class C:
        pass
    C_classdef = bk.getclassdef(C)
    si1 = SomeInstance(C_classdef)
    C_classdef.revision += 1
    si2 = SomeInstance(C_classdef)

    assert s1.contains(si1)
    assert si1.contains(si1)
    assert si1.contains(s6)

    assert si2.contains(si1)
    assert not si1.contains(si2)
    assert si1.contains(si2) is RevDiff

    # dicts

    sd1 = SomeDict({}, SomeString(), s1)
    sd6 = SomeDict({}, SomeString(), s6)
    sdi1 = SomeDict({}, SomeString(), si1)
    sdi2 = SomeDict({}, SomeString(), si2)
    sdi3 = SomeDict({}, SomeInteger(), si1)

    assert sd1.contains(sdi1)
    assert sdi1.contains(sdi1)
    assert sdi1.contains(sd6)

    assert sdi2.contains(sdi1)
    assert not sdi1.contains(sdi2)
    assert sdi1.contains(sdi2) is RevDiff

    assert not sdi1.contains(sdi3)
    assert sdi1.contains(sdi3) is False
    assert not sdi3.contains(sdi1)
    assert sdi3.contains(sdi1) is False

    sdx = SomeDict({}, si1, SomeString())
    sdy = SomeDict({}, si2, SomeString())

    assert sdy.contains(sdx)
    assert not sdx.contains(sdy)
    assert sdx.contains(sdy) is RevDiff

    sdz = SomeDict({}, si1, SomeInteger())
    
    assert not sdz.contains(sdx)
    assert not sdx.contains(sdz)
    assert sdz.contains(sdx) is False
    assert sdx.contains(sdz) is False

    # tuples

    st1 = SomeTuple((SomeString(), s1))
    st6 = SomeTuple((SomeString(), s6))
    sti1 = SomeTuple((SomeString(), si1))
    sti2 = SomeTuple((SomeString(), si2))
    sti3 = SomeTuple((SomeInteger(), si1))

    assert st1.contains(sti1)
    assert sti1.contains(sti1)
    assert sti1.contains(st6)

    assert sti2.contains(sti1)
    assert not sti1.contains(sti2)
    assert sti1.contains(sti2) is RevDiff

    assert not sti1.contains(sti3)
    assert sti1.contains(sti3) is False
    assert not sti3.contains(sti1)
    assert sti3.contains(sti1) is False

    stx = SomeTuple((si1, SomeString()))
    sty = SomeTuple((si2, SomeString()))

    assert sty.contains(stx)
    assert not stx.contains(sty)
    assert stx.contains(sty) is RevDiff

    stz = SomeTuple((si1, SomeInteger()))
    
    assert not stz.contains(stx)
    assert not stx.contains(stz)
    assert stz.contains(stx) is False
    assert stx.contains(stz) is False

    C_classdef.revision += 1
    si3 = SomeInstance(C_classdef)

    sti12 = SomeTuple((si1,si2))
    sti23 = SomeTuple((si2,si3))

    assert sti23.contains(sti12)
    assert not sti12.contains(sti23)
    assert sti12.contains(sti23) is RevDiff
    


def test_union():
    assert ([unionof(s,t) for s in slist for t in slist] ==
            [s1, s1, s1, s1, s1, s1, s1,
             s1, s2, s3, s1, s1, s2, s2,
             s1, s3, s3, s1, s1, s3, s3,
             s1, s1, s1, s4, s5, s4, s1,
             s1, s1, s1, s5, s5, s5, s1,
             s1, s2, s3, s4, s5, s6, s7,
             s1, s2, s3, s1, s1, s7, s7])

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

if __name__ == '__main__':
    for name, value in globals().items():
        if name.startswith('test_'):
            value()
