from pypy.translator.interactive import Translation
from pypy import conftest
from pypy.rpython.lltypesystem import llmemory, lltype
from pypy.rlib.objectmodel import ComputedIntSymbolic

def getcompiled(f, args):
    t = Translation(f)
    fn = t.compile_c(args)
    if conftest.option.view:
        t.view()
    return fn, t

def test_offsetof():
    STRUCT = lltype.GcStruct("s", ("x", lltype.Signed), ("y", lltype.Signed))
    offsetx = llmemory.offsetof(STRUCT, 'x')
    offsety = llmemory.offsetof(STRUCT, 'y')
    def f():
        s = lltype.malloc(STRUCT)
        s.x = 1
        adr = llmemory.cast_ptr_to_adr(s)
        result = (adr + offsetx).signed[0]
        (adr + offsety).signed[0] = 2
        return result * 10 + s.y
    fn, t = getcompiled(f, [])
    res = fn()
    assert res == 12

def test_sizeof_array_with_no_length():
    A = lltype.Array(lltype.Signed, hints={'nolength': True})
    arraysize = llmemory.sizeof(A, 10)
    signedsize = llmemory.sizeof(lltype.Signed)
    def f():
        return arraysize-signedsize*10
    fn, t = getcompiled(f, [])
    res = fn()
    assert res == 0

def test_itemoffsetof():
    ARRAY = lltype.GcArray(lltype.Signed)
    itemoffsets = [llmemory.itemoffsetof(ARRAY, i) for i in range(5)]
    def f():
        a = lltype.malloc(ARRAY, 5)
        adr = llmemory.cast_ptr_to_adr(a)
        result = 0
        for i in range(5):
            a[i] = i + 1
        for i in range(5):
            result = result * 10 + (adr + itemoffsets[i]).signed[0]
        for i in range(5):
            (adr + itemoffsets[i]).signed[0] = i
        for i in range(5):
            result = 10 * result + a[i]
        return result
    fn, t = getcompiled(f, [])
    res = fn()
    assert res == 1234501234

def test_itemoffsetof_fixedsizearray():
    ARRAY = lltype.FixedSizeArray(lltype.Signed, 5)
    itemoffsets = [llmemory.itemoffsetof(ARRAY, i) for i in range(5)]
    a = lltype.malloc(ARRAY, immortal=True)
    def f():
        adr = llmemory.cast_ptr_to_adr(a)
        result = 0
        for i in range(5):
            a[i] = i + 1
        for i in range(5):
            result = result * 10 + (adr + itemoffsets[i]).signed[0]
        for i in range(5):
            (adr + itemoffsets[i]).signed[0] = i
        for i in range(5):
            result = 10 * result + a[i]
        return result
    fn, t = getcompiled(f, [])
    res = fn()
    assert res == 1234501234

def test_sizeof_constsize_struct():
    # _not_ a GcStruct, since we want to raw_malloc it
    STRUCT = lltype.Struct("s", ("x", lltype.Signed), ("y", lltype.Signed))
    STRUCTPTR = lltype.Ptr(STRUCT)
    sizeofs = llmemory.sizeof(STRUCT)
    offsety = llmemory.offsetof(STRUCT, 'y')
    def f():
        adr = llmemory.raw_malloc(sizeofs)
        s = llmemory.cast_adr_to_ptr(adr, STRUCTPTR)
        s.y = 5 # does not crash
        result = (adr + offsety).signed[0] * 10 + int(offsety < sizeofs)
        llmemory.raw_free(adr)
        return result
    fn, t = getcompiled(f, [])
    res = fn()
    assert res == 51

def test_computed_int_symbolic():
    too_early = True
    def compute_fn():
        assert not too_early
        return 7
    k = ComputedIntSymbolic(compute_fn)
    def f():
        return k*6

    t = Translation(f)
    t.rtype()
    if conftest.option.view:
        t.view()
    too_early = False
    fn = t.compile_c()
    res = fn()
    assert res == 42
