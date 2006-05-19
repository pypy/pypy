from pypy.rpython.lltypesystem.lloperation import LL_OPERATIONS, llop
from pypy.rpython.llinterp import LLFrame
from pypy.rpython.test.test_llinterp import interpret

# This tests that the LLInterpreter and the LL_OPERATIONS tables are in sync.

LL_INTERP_OPERATIONS = [name[3:] for name in LLFrame.__dict__.keys()
                                 if name.startswith('op_')
# Ignore OO operations for now
                                    and not (name == 'op_new' or
                                             name == 'op_subclassof' or
                                             name == 'op_instanceof' or
                                             name == 'op_classof' or
                                             name == 'op_runtimenew' or
                                             name.startswith('op_oo'))]


def test_table_complete():
    for opname in LL_INTERP_OPERATIONS:
        assert opname in LL_OPERATIONS

def test_llinterp_complete():
    for opname in LL_OPERATIONS:
        if opname.startswith('gc_x_'):
            continue   # ignore experimental stuff
        assert opname in LL_INTERP_OPERATIONS

def test_llop():
    from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
    from pypy.rpython.lltypesystem import lltype
    def llf(x, y):
        return llop.int_add(lltype.Signed, x, y)
    res = interpret(llf, [5, 7], policy=LowLevelAnnotatorPolicy())
    assert res == 12
