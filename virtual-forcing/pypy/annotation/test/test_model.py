
import autopath
import py
from pypy.annotation.model import *
from pypy.annotation.listdef import ListDef, MOST_GENERAL_LISTDEF
from pypy.rpython.ootypesystem.ootype import ROOT


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
        self.name = cls.__name__

si0 = SomeInstance(DummyClassDef(), True)
si1 = SomeInstance(DummyClassDef())
sTrue = SomeBool()
sTrue.const = True
sFalse = SomeBool()
sFalse.const = False

def test_is_None():
    assert pair(s_None, s_None).is_() == sTrue
    assert pair(si1, s_None).is_() == sFalse
    assert pair(si0, s_None).is_() != sTrue
    assert pair(si0, s_None).is_() != sFalse
    assert pair(si0, s_None).is_() == SomeBool()

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
    s2 = SomeList(MOST_GENERAL_LISTDEF)
    assert s1 != s2
    assert s2.contains(s1)
    assert s1 != s2
    assert not s1.contains(s2)
    assert s1 != s2

def test_ll_to_annotation():
    s_z = ll_to_annotation(lltype.Signed._defl())
    s_s = SomeInteger()
    s_u = SomeInteger(nonneg=True, unsigned=True)
    assert s_z.contains(s_s)
    assert not s_z.contains(s_u)
    s_uz = ll_to_annotation(lltype.Unsigned._defl())
    assert s_uz.contains(s_u)
    assert ll_to_annotation(lltype.Bool._defl()).contains(SomeBool())
    assert ll_to_annotation(lltype.Char._defl()).contains(SomeChar())
    S = lltype.GcStruct('s')
    A = lltype.GcArray()
    s_p = ll_to_annotation(lltype.malloc(S))
    assert isinstance(s_p, SomePtr) and s_p.ll_ptrtype == lltype.Ptr(S)
    s_p = ll_to_annotation(lltype.malloc(A, 0))
    assert isinstance(s_p, SomePtr) and s_p.ll_ptrtype == lltype.Ptr(A)
    C = ootype.Instance('C', ROOT, {})
    s_p = ll_to_annotation(ootype.new(C))
    assert isinstance(s_p, SomeOOInstance) and s_p.ootype == C

def test_annotation_to_lltype():
    from pypy.rlib.rarithmetic import r_uint
    s_i = SomeInteger()
    s_pos = SomeInteger(nonneg=True)
    s_1 = SomeInteger(nonneg=True); s_1.const = 1
    s_m1 = SomeInteger(nonneg=False); s_m1.const = -1
    s_u = SomeInteger(nonneg=True, unsigned=True); 
    s_u1 = SomeInteger(nonneg=True, unsigned=True); 
    s_u1.const = r_uint(1)
    assert annotation_to_lltype(s_i) == lltype.Signed
    assert annotation_to_lltype(s_pos) == lltype.Signed
    assert annotation_to_lltype(s_1) == lltype.Signed
    assert annotation_to_lltype(s_m1) == lltype.Signed
    assert annotation_to_lltype(s_u) == lltype.Unsigned
    assert annotation_to_lltype(s_u1) == lltype.Unsigned
    assert annotation_to_lltype(SomeBool()) == lltype.Bool
    assert annotation_to_lltype(SomeChar()) == lltype.Char
    PS = lltype.Ptr(lltype.GcStruct('s'))
    s_p = SomePtr(ll_ptrtype=PS)
    assert annotation_to_lltype(s_p) == PS
    py.test.raises(ValueError, "annotation_to_lltype(si0)")
    C = ootype.Instance('C', ROOT, {})
    ref = SomeOOInstance(C)
    assert annotation_to_lltype(ref) == C
    
def test_ll_union():
    PS1 = lltype.Ptr(lltype.GcStruct('s'))
    PS2 = lltype.Ptr(lltype.GcStruct('s'))
    PS3 = lltype.Ptr(lltype.GcStruct('s3'))
    PA1 = lltype.Ptr(lltype.GcArray())
    PA2 = lltype.Ptr(lltype.GcArray())

    assert unionof(SomePtr(PS1),SomePtr(PS1)) == SomePtr(PS1)
    assert unionof(SomePtr(PS1),SomePtr(PS2)) == SomePtr(PS2)
    assert unionof(SomePtr(PS1),SomePtr(PS2)) == SomePtr(PS1)

    assert unionof(SomePtr(PA1),SomePtr(PA1)) == SomePtr(PA1)
    assert unionof(SomePtr(PA1),SomePtr(PA2)) == SomePtr(PA2)
    assert unionof(SomePtr(PA1),SomePtr(PA2)) == SomePtr(PA1)

    assert unionof(SomePtr(PS1),SomeImpossibleValue()) == SomePtr(PS1)
    assert unionof(SomeImpossibleValue(), SomePtr(PS1)) == SomePtr(PS1)

    py.test.raises(AssertionError, "unionof(SomePtr(PA1), SomePtr(PS1))")
    py.test.raises(AssertionError, "unionof(SomePtr(PS1), SomePtr(PS3))")
    py.test.raises(AssertionError, "unionof(SomePtr(PS1), SomeInteger())")
    py.test.raises(AssertionError, "unionof(SomePtr(PS1), SomeObject())")
    py.test.raises(AssertionError, "unionof(SomeInteger(), SomePtr(PS1))")
    py.test.raises(AssertionError, "unionof(SomeObject(), SomePtr(PS1))")

def test_oo_union():
    C1 = ootype.Instance("C1", ROOT)
    C2 = ootype.Instance("C2", C1)
    C3 = ootype.Instance("C3", C1)
    D = ootype.Instance("D", ROOT)
    assert unionof(SomeOOInstance(C1), SomeOOInstance(C1)) == SomeOOInstance(C1)
    assert unionof(SomeOOInstance(C1), SomeOOInstance(C2)) == SomeOOInstance(C1)
    assert unionof(SomeOOInstance(C2), SomeOOInstance(C1)) == SomeOOInstance(C1)
    assert unionof(SomeOOInstance(C2), SomeOOInstance(C3)) == SomeOOInstance(C1)

    assert unionof(SomeOOInstance(C1),SomeImpossibleValue()) == SomeOOInstance(C1)
    assert unionof(SomeImpossibleValue(), SomeOOInstance(C1)) == SomeOOInstance(C1)

    assert unionof(SomeOOInstance(C1), SomeOOInstance(D)) == SomeOOInstance(ROOT)

def test_ooclass_array_contains():
    A = ootype.Array(ootype.Signed)
    cls = ootype.runtimeClass(A)
    s1 = SomeOOClass(A)
    s2 = SomeOOClass(A)
    s2.const=cls
    assert s1.contains(s2)

if __name__ == '__main__':
    for name, value in globals().items():
        if name.startswith('test_'):
            value()

