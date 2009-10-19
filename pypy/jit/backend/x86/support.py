
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated

CHUNK_SIZE = 1000

def new_nonmovable_growable_array(TP):
    ATP = lltype.GcArray(TP)
    
    class NonmovableGrowableArray(object):
        def __init__(self):
            self.chunks = []
            self.lgt = 0

        def _grow(self):
            # XXX workaround for a fact that rgc.malloc_nonmovable always
            #     returns nullptr when run on top of python
            if we_are_translated():
                new_item = rgc.malloc_nonmovable(ATP, CHUNK_SIZE, zero=True)
            else:
                new_item = lltype.malloc(ATP, CHUNK_SIZE, zero=True)
            self.chunks.append(new_item)
            self.lgt += 1

        def get_addr_for_num(self, i):
            chunk_no, ofs = self._no_of(i)
            chunk = self.chunks[chunk_no]
            rffi.cast(lltype.Signed, chunk)
            return rffi.cast(lltype.Signed, lltype.direct_ptradd(
                lltype.direct_arrayitems(chunk), ofs))

        def _no_of(self, i):
            while i >= len(self.chunks) * CHUNK_SIZE:
                self._grow()
            return i / CHUNK_SIZE, i % CHUNK_SIZE

        def setitem(self, i, v):
            chunk_no, ofs = self._no_of(i)
            self.chunks[chunk_no][ofs] = v

        def getitem(self, i):
            chunk_no, ofs = self._no_of(i)
            return self.chunks[chunk_no][ofs]

    return NonmovableGrowableArray

NonmovableGrowableArrayFloat = new_nonmovable_growable_array(lltype.Float)
NonmovableGrowableArraySigned = new_nonmovable_growable_array(lltype.Signed)
NonmovableGrowableArrayGCREF = new_nonmovable_growable_array(llmemory.GCREF)
