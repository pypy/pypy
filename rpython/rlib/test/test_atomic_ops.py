from pypy.rlib.atomic_ops import bool_cas
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


ARRAY = rffi.CArray(llmemory.Address)

def test_bool_cas():
    a = lltype.malloc(ARRAY, 1, flavor='raw')
    a[0] = rffi.cast(llmemory.Address, 42)
    #
    res = bool_cas(rffi.cast(llmemory.Address, a),
                   rffi.cast(llmemory.Address, 42),
                   rffi.cast(llmemory.Address, 43))
    assert res == True
    assert rffi.cast(lltype.Signed, a[0]) == 43
    #
    res = bool_cas(rffi.cast(llmemory.Address, a),
                   rffi.cast(llmemory.Address, 42),
                   rffi.cast(llmemory.Address, 44))
    assert res == False
    assert rffi.cast(lltype.Signed, a[0]) == 43
    #
    lltype.free(a, flavor='raw')
    return 0

def test_translate_bool_cas():
    from pypy.translator.c.test.test_genc import compile

    f = compile(test_bool_cas, [])
    res = f()
    assert res == 0
