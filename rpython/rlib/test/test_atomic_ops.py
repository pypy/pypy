from rpython.rlib.atomic_ops import bool_cas, fetch_and_add
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi


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

def test_fetch_and_add():
    a = lltype.malloc(ARRAY, 1, flavor='raw')
    a[0] = rffi.cast(llmemory.Address, 42)
    #
    res = fetch_and_add(rffi.cast(llmemory.Address, a), -2)
    assert res == 42
    assert rffi.cast(lltype.Signed, a[0]) == 40
    res = fetch_and_add(rffi.cast(llmemory.Address, a), 3)
    assert res == 40
    assert rffi.cast(lltype.Signed, a[0]) == 43
    #
    lltype.free(a, flavor='raw')

def test_translate():
    from rpython.translator.c.test.test_genc import compile

    def llf():
        test_bool_cas()
        test_fetch_and_add()
        return 0

    f = compile(llf, [])
    res = f()
    assert res == 0
