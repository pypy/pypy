from pypy.translator.annrpython import RPythonAnnotator
from pypy.rpython.annlowlevel import annotate_lowlevel_helper
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.annotation import model as annmodel


# ____________________________________________________________

def ll_rtype(llfn, argtypes=[]):
    a = RPythonAnnotator()
    s, dontcare = annotate_lowlevel_helper(a, llfn, argtypes)
    t = a.translator
    typer = RPythonTyper(a)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return s, t

def test_cast_pointer():
    S = GcStruct('s', ('x', Signed))
    S1 = GcStruct('s1', ('sub', S))
    S2 = GcStruct('s2', ('sub', S1))
    PS = Ptr(S)
    PS2 = Ptr(S2)
    def lldown(p):
        return cast_pointer(PS, p)
    s, t = ll_rtype(lldown, [annmodel.SomePtr(PS2)])
    assert s.ll_ptrtype == PS
    def llup(p):
        return cast_pointer(PS2, p)
    s, t = ll_rtype(llup, [annmodel.SomePtr(PS)])
    assert s.ll_ptrtype == PS2
