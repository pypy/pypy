import py
from pypy.rpython.lltypesystem.lloperation import LL_OPERATIONS, llop
from pypy.rpython.lltypesystem import lltype, opimpl
from pypy.rpython.ootypesystem import ootype, ooopimpl
from pypy.rpython.llinterp import LLFrame
from pypy.rpython.test.test_llinterp import interpret

LL_INTERP_OPERATIONS = [name[3:] for name in LLFrame.__dict__.keys()
                                 if name.startswith('op_')]

# ____________________________________________________________

def test_canfold_opimpl_complete():
    for opname, llop in LL_OPERATIONS.items():
        assert opname == llop.opname
        if llop.canfold:
            if llop.oo:
                func = ooopimpl.get_op_impl(opname)
            else:
                func = opimpl.get_op_impl(opname)
            assert callable(func)

def test_llop_fold():
    assert llop.int_add(lltype.Signed, 10, 2) == 12
    assert llop.int_add(lltype.Signed, -6, -7) == -13
    S1 = lltype.GcStruct('S1', ('x', lltype.Signed), hints={'immutable': True})
    s1 = lltype.malloc(S1)
    s1.x = 123
    assert llop.getfield(lltype.Signed, s1, 'x') == 123
    S2 = lltype.GcStruct('S2', ('x', lltype.Signed))
    s2 = lltype.malloc(S2)
    s2.x = 123
    py.test.raises(TypeError, "llop.getfield(lltype.Signed, s2, 'x')")

def test_llop_interp():
    from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
    def llf(x, y):
        return llop.int_add(lltype.Signed, x, y)
    res = interpret(llf, [5, 7], policy=LowLevelAnnotatorPolicy())
    assert res == 12

# ___________________________________________________________________________
# This tests that the LLInterpreter and the LL_OPERATIONS tables are in sync.

def test_table_complete():
    for opname in LL_INTERP_OPERATIONS:
        assert opname in LL_OPERATIONS

def test_llinterp_complete():
    for opname, llop in LL_OPERATIONS.items():
        if llop.canfold:
            continue
        if opname.startswith('gc_x_') or opname.startswith('llvm_'):
            continue   # ignore experimental stuff
        assert opname in LL_INTERP_OPERATIONS
