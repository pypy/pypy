import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator import HintAnnotator
from pypy.jit.hintbookkeeper import HintBookkeeper
from pypy.jit.hintmodel import *
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import hint
from pypy.annotation import model as annmodel
from pypy.annotation.policy import AnnotatorPolicy

P_OOPSPEC = AnnotatorPolicy()
P_OOPSPEC.oopspec = True

def hannotate(func, argtypes, policy=None, annotator=False):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(func, argtypes)
    rtyper = t.buildrtyper()
    rtyper.specialize()
    graph1 = graphof(t, func)
    # build hint annotator types
    hannotator = HintAnnotator(policy=policy)
    hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                {OriginFlags(): True})
                                         for v in graph1.getargs()])
    t = hannotator.translator
    #t.view()
    if annotator:
        return hs, hannotator
    else:
        return hs

def test_simple():
    def ll_function(x, y):
        return x + y
    hs = hannotate(ll_function, [int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert len(hs.origins) == 3
    assert hs.concretetype == lltype.Signed

def test_join():
    def ll_function(cond, x,y):
        if cond:
            z = x+y
        else:
            z = x-y
        return z
    hs = hannotate(ll_function, [bool, int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert len(hs.origins) == 4
    assert hs.concretetype == lltype.Signed


def test_simple_hint_result():
    def ll_function(cond, x,y):
        if cond:
            z = x+y
        else:
            z = x-y
        z = hint(z, concrete=True)
        return z
    hs = hannotate(ll_function, [bool, int, int])
    assert isinstance(hs, SomeLLConcreteValue)
    assert hs.concretetype == lltype.Signed
  
def test_simple_hint_origins():
    def ll_function(cond, x,y):
        if cond:
            z = x+y
        else:
            z = x-y
        z1 = hint(z, concrete=True)
        return z # origin of z1
    hs = hannotate(ll_function, [bool, int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert len(hs.origins) == 4
    for o in hs.origins:
        assert o.fixed
    assert hs.concretetype == lltype.Signed
 
def test_simple_variable():
    def ll_function(x,y):
        x = hint(x, variable=True) # special hint only for testing purposes!!!
        return x + y
    hs = hannotate(ll_function, [int, int])
    assert type(hs) is SomeLLAbstractVariable
    assert hs.concretetype == lltype.Signed
    
def test_simple_concrete_propagation():
    def ll_function(x,y):
        x = hint(x, concrete=True)
        return x + y
    hs = hannotate(ll_function, [int, int])
    assert type(hs) is SomeLLConcreteValue
    assert hs.concretetype == lltype.Signed

def test_union():
    unionof = annmodel.unionof
    av1, av2 = SomeLLAbstractVariable(lltype.Signed), SomeLLAbstractVariable(lltype.Signed)
    cv1, cv2 = SomeLLConcreteValue(lltype.Signed), SomeLLConcreteValue(lltype.Signed)
    ac1, ac2 = SomeLLAbstractConstant(lltype.Signed, {}), SomeLLAbstractConstant(lltype.Signed, {})
    ac3 = SomeLLAbstractConstant(lltype.Signed, {})
    ac3.const = 3
    ac4 = SomeLLAbstractConstant(lltype.Signed, {})
    ac4.const = 4
    assert unionof(av1, av2) == av1
    assert unionof(cv1, cv2) == cv2
    assert unionof(ac1, ac2) == ac1
    assert unionof(ac3, ac3) == ac3
    assert unionof(ac3, ac2) == ac1
    assert unionof(ac4, ac3) == ac1
    # degenerating cases
    py.test.raises(annmodel.UnionError, "unionof(cv1, av1)")
    py.test.raises(annmodel.UnionError, "unionof(av1, cv1)")

    # MAYBE...
    #py.test.raises(annmodel.UnionError, "unionof(ac1, cv1)")
    #py.test.raises(annmodel.UnionError, "unionof(cv1, ac1)")
    assert unionof(cv1, ac1) == cv1
    assert unionof(ac1, cv1) == cv1
    
    # constant with values
    assert unionof(av1, ac1) == av1
    assert unionof(ac1, av1) == av1
    assert unionof(ac3, av1) == av1
    assert unionof(av2, ac4) == av1

def test_op_meet():
    def meet(hs1, hs2):
        HintBookkeeper(None).enter(None)
        return pair(hs1, hs2).int_add()
    av1, av2 = SomeLLAbstractVariable(lltype.Signed), SomeLLAbstractVariable(lltype.Signed)
    cv1, cv2 = SomeLLConcreteValue(lltype.Signed), SomeLLConcreteValue(lltype.Signed)
    ac1, ac2 = SomeLLAbstractConstant(lltype.Signed, {}), SomeLLAbstractConstant(lltype.Signed, {})
    assert meet(av1, av2) == av1
    assert meet(cv1, cv2) == cv2
    assert isinstance(meet(ac1, ac2), SomeLLAbstractConstant)
    assert meet(ac1, cv1) == cv1
    assert meet(cv1, ac1) == cv1
    assert meet(av1, cv1) == av1
    assert meet(cv1, av1) == av1
    assert meet(ac1, av1) == av1
    assert meet(av1, ac1) == av1

def test_loop():
    def ll_function(x, y):
        while x > 0:
            y += x
            x -= 1
        return y
    hs = hannotate(ll_function, [int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 4

def test_loop1():
    def ll_function(x, y):
        while x > 0:
            x1 = hint(x, concrete=True)
            if x1 == 7:
                y += x
            x -= 1
        return y
    hs = hannotate(ll_function, [int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 4

def test_simple_struct():
    S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                      ('world', lltype.Signed),
                        hints={'immutable': True})
    def ll_function(s):
        return s.hello * s.world
    hs = hannotate(ll_function, [annmodel.SomePtr(lltype.Ptr(S))])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 4

def test_simple_struct_malloc():
    S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                      ('world', lltype.Signed))               
    def ll_function(x):
        s = lltype.malloc(S)
        s.hello = x
        return s.hello + s.world

    hs = hannotate(ll_function, [int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 2

def test_container_union():
    S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                      ('world', lltype.Signed))               
    def ll_function(cond, x, y):
        if cond:
            s = lltype.malloc(S)
            s.hello = x
        else:
            s = lltype.malloc(S)
            s.world = y
        return s.hello + s.world

    hs = hannotate(ll_function, [bool, int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 3

def test_simple_call():
    def ll2(x, y, z):
        return x + (y + 42)
    def ll1(x, y, z):
        return ll2(x, y - z, x + y + z)
    hs = hannotate(ll1, [int, int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 5

def test_simple_list_operations():
    def ll_function(x, y, index):
        l = [x]
        l.append(y)
        return l[index]
    hs = hannotate(ll_function, [int, int, int], policy=P_OOPSPEC)
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 2

def test_some_more_list_operations():
    def ll_function(x, y, index):
        l = []
        l.append(x)
        l[0] = y
        return (l+list(l))[index]
    hs = hannotate(ll_function, [int, int, int], policy=P_OOPSPEC)
    assert isinstance(hs, SomeLLAbstractConstant)
    assert hs.concretetype == lltype.Signed
    assert len(hs.origins) == 2

def test_simple_cast_pointer():
    GCS1 = lltype.GcStruct('s1', ('x', lltype.Signed))
    GCS2 = lltype.GcStruct('s2', ('sub', GCS1), ('y', lltype.Signed))
    PGCS1 = lltype.Ptr(GCS1)
    PGCS2 = lltype.Ptr(GCS2)
    def ll1():
        s2 = lltype.malloc(GCS2)
        return lltype.cast_pointer(PGCS1, s2)
    hs = hannotate(ll1, [])
    assert isinstance(hs, SomeLLAbstractContainer)
    assert hs.concretetype == PGCS1
    def ll1():
        s2 = lltype.malloc(GCS2)
        s1 = s2.sub
        return lltype.cast_pointer(PGCS2, s1)
    hs = hannotate(ll1, [])
    assert isinstance(hs, SomeLLAbstractContainer)
    assert hs.concretetype == PGCS2

def test_getarrayitem():
    A = lltype.GcArray(lltype.Signed, hints={'immutable': True})
    a = lltype.malloc(A, 10)
    def ll1(n):
        v = a[n]
        v = hint(v, concrete=True)
        return v
    hs, ha = hannotate(ll1, [int], annotator=True)
    assert isinstance(hs, SomeLLConcreteValue)
    g1 = graphof(ha.translator, ll1)
    hs_n = ha.binding(g1.getargs()[0])
    assert hs_n.origins.keys()[0].fixed

def test_getvarrayitem():
    A = lltype.GcArray(lltype.Signed, hints={'immutable': True})
    def ll1(n):
        a = lltype.malloc(A, 10)
        v = a[n]
        v = hint(v, concrete=True)
        return v
    hs, ha = hannotate(ll1, [int], annotator=True)
    assert isinstance(hs, SomeLLConcreteValue)
    g1 = graphof(ha.translator, ll1)
    hs_n = ha.binding(g1.getargs()[0])
    assert hs_n.origins.keys()[0].fixed
 
def test_hannotate_tl():
    from pypy.jit import tl
    hannotate(tl.interp, [str, int], policy=P_OOPSPEC)
