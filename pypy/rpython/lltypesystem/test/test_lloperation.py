from pypy.rpython.lltypesystem.lloperation import LL_OPERATIONS
from pypy.rpython.llinterp import LLFrame

# This tests that the LLInterpreter and the LL_OPERATIONS tables are in sync.

LL_INTERP_OPERATIONS = [name[3:] for name in LLFrame.__dict__.keys()
                                 if name.startswith('op_')
# Ignore OO operations for now
                                    and not (name == 'op_new' or
                                             name == 'op_subclassof' or
                                             name == 'op_instanceof' or
                                             name == 'op_classof' or
                                             name.startswith('op_oo'))]


def test_table_complete():
    for opname in LL_INTERP_OPERATIONS:
        assert opname in LL_OPERATIONS

def test_llinterp_complete():
    for opname in LL_OPERATIONS:
        assert opname in LL_INTERP_OPERATIONS
