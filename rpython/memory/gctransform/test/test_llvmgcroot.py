from rpython.memory.gctransform.llvmgcroot import SHAPE_PTR, GCMAP, hashtable_create, hashtable_get, hashtable_free
from rpython.rtyper.lltypesystem import lltype, llmemory


class _Stub(object):
    def __getattr__(self, attr):
        return self
    def __call__(self, *args, **kwds):
        return None

def test_hashtable():
    gcmap = lltype.malloc(GCMAP, 3, flavor='raw', zero=True)
    gcmap[0].safe_point = llmemory.cast_int_to_adr(221)
    gcmap[0].shape = lltype.cast_int_to_ptr(SHAPE_PTR, 2201)
    gcmap[1].safe_point = llmemory.cast_int_to_adr(331)
    gcmap[1].shape = lltype.cast_int_to_ptr(SHAPE_PTR, 3301)
    # hash collision
    gcmap[2].safe_point = llmemory.cast_int_to_adr(131)
    gcmap[2].shape = lltype.cast_int_to_ptr(SHAPE_PTR, 1101)

    gcdata = _Stub()
    hashtable_create(gcdata, gcmap)

    assert hashtable_get(gcdata, llmemory.cast_int_to_adr(221)) == \
            lltype.cast_int_to_ptr(SHAPE_PTR, 2201)
    assert hashtable_get(gcdata, llmemory.cast_int_to_adr(331)) == \
            lltype.cast_int_to_ptr(SHAPE_PTR, 3301)
    assert hashtable_get(gcdata, llmemory.cast_int_to_adr(131)) == \
            lltype.cast_int_to_ptr(SHAPE_PTR, 1101)

    hashtable_free(gcdata)
    lltype.free(gcmap, flavor='raw')
