from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.translator.stm.stmgcintf import StmOperations

stm_operations = StmOperations()


def test_set_get_del():
    # assume that they are really thread-local; not checked here
    s = lltype.malloc(lltype.Struct('S'), flavor='raw')
    a = llmemory.cast_ptr_to_adr(s)
    stm_operations.set_tls(a)
    assert stm_operations.get_tls() == a
    stm_operations.del_tls()
    lltype.free(s, flavor='raw')
