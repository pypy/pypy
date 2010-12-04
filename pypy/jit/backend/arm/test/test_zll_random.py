from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.test import test_ll_random
from pypy.jit.backend.test import test_random
from pypy.jit.backend.test.test_ll_random import LLtypeOperationBuilder
from pypy.jit.backend.test.test_random import check_random_function, Random
from pypy.jit.metainterp.resoperation import rop

# XXX Remove this list from here once all operations work and use the default
# one
OPERATIONS = test_random.OPERATIONS[:]

for i in range(4):      # make more common
    OPERATIONS.append(test_ll_random.GetFieldOperation(rop.GETFIELD_GC))
    OPERATIONS.append(test_ll_random.GetFieldOperation(rop.GETFIELD_GC))
    OPERATIONS.append(test_ll_random.SetFieldOperation(rop.SETFIELD_GC))
    OPERATIONS.append(test_ll_random.NewOperation(rop.NEW))
    OPERATIONS.append(test_ll_random.NewOperation(rop.NEW_WITH_VTABLE))
#
#    OPERATIONS.append(test_ll_random.GetArrayItemOperation(rop.GETARRAYITEM_GC))
#    OPERATIONS.append(test_ll_random.GetArrayItemOperation(rop.GETARRAYITEM_GC))
#    OPERATIONS.append(test_ll_random.SetArrayItemOperation(rop.SETARRAYITEM_GC))
#    #OPERATIONS.append(test_ll_random.NewArrayOperation(rop.NEW_ARRAY))
#    OPERATIONS.append(test_ll_random.ArrayLenOperation(rop.ARRAYLEN_GC))
#    #OPERATIONS.append(test_ll_random.NewStrOperation(rop.NEWSTR))
#    #OPERATIONS.append(test_ll_random.NewUnicodeOperation(rop.NEWUNICODE))
#    OPERATIONS.append(test_ll_random.StrGetItemOperation(rop.STRGETITEM))
#    OPERATIONS.append(test_ll_random.UnicodeGetItemOperation(rop.UNICODEGETITEM))
#    OPERATIONS.append(test_ll_random.StrSetItemOperation(rop.STRSETITEM))
#    OPERATIONS.append(test_ll_random.UnicodeSetItemOperation(rop.UNICODESETITEM))
#    OPERATIONS.append(test_ll_random.StrLenOperation(rop.STRLEN))
#    OPERATIONS.append(test_ll_random.UnicodeLenOperation(rop.UNICODELEN))
#
#for i in range(2):
    #OPERATIONS.append(test_ll_random.GuardClassOperation(rop.GUARD_CLASS))
    #OPERATIONS.append(test_ll_random.CallOperation(rop.CALL))
    #OPERATIONS.append(test_ll_random.RaisingCallOperation(rop.CALL))
    #OPERATIONS.append(test_ll_random.RaisingCallOperationGuardNoException(rop.CALL))
    #OPERATIONS.append(test_ll_random.RaisingCallOperationWrongGuardException(rop.CALL))
    #OPERATIONS.append(test_ll_random.CallOperationException(rop.CALL))
#OPERATIONS.append(test_ll_random.GuardNonNullClassOperation(rop.GUARD_NONNULL_CLASS))



LLtypeOperationBuilder.OPERATIONS = OPERATIONS

CPU = getcpuclass()

def test_stress():
    cpu = CPU(None, None)
    r = Random()
    for i in range(1000):
        check_random_function(cpu, LLtypeOperationBuilder, r, i, 1000)
