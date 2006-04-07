import py
from pypy.translator.interactive import Translation
from pypy import conftest
from pypy.rpython.lltypesystem import llmemory, lltype
from pypy.rpython.memory import lladdress
from pypy.rpython.objectmodel import ComputedIntSymbolic

from pypy.translator.llvm.test.runtest import compile_function

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
    fn = compile_function(f, [])
    res = fn()
    assert res == 12

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
    fn = compile_function(f, [])
    res = fn()
    assert res == 12

def test_sizeof_array_with_no_length():
    py.test.skip("inprogress")
    A = lltype.GcArray(lltype.Signed, hints={'nolength': True})
    a = lltype.malloc(A, 5)
    
    arraysize = llmemory.itemoffsetof(A, 10)
    signedsize = llmemory.sizeof(lltype.Signed)
    def f():
        return a[0] + arraysize-signedsize*10
    fn = compile_function(f, [])
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
    fn = compile_function(f, [])
    res = fn()
    assert res == 1234501234

def test_sizeof_constsize_struct():
    # _not_ a GcStruct, since we want to raw_malloc it
    STRUCT = lltype.Struct("s", ("x", lltype.Signed), ("y", lltype.Signed))
    STRUCTPTR = lltype.Ptr(STRUCT)
    sizeofs = llmemory.sizeof(STRUCT)
    offsety = llmemory.offsetof(STRUCT, 'y')
    def f():
        adr = lladdress.raw_malloc(sizeofs)
        s = llmemory.cast_adr_to_ptr(adr, STRUCTPTR)
        s.y = 5 # does not crash
        result = (adr + offsety).signed[0] * 10 + int(offsety < sizeofs)
        lladdress.raw_free(adr)
        return result

    fn = compile_function(f, [])
    res = fn()
    assert res == 51

def test_computed_int_symbolic():
    def compute_fn():
        return 7
    k = ComputedIntSymbolic(compute_fn)
    def f():
        return k*6

    fn = compile_function(f, [])
    res = fn()
    assert res == 42
