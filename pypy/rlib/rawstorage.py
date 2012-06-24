
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.annotation import model as annmodel
from pypy.rlib.rgc import lltype_is_gc

RAW_STORAGE = rffi.CCHARP.TO
RAW_STORAGE_PTR = rffi.CCHARP

def alloc_raw_storage(size):
    return lltype.malloc(RAW_STORAGE, size, flavor='raw')

def raw_storage_setitem(storage, index, item):
    # NOT_RPYTHON
    TP = rffi.CArrayPtr(lltype.typeOf(item))
    rffi.cast(TP, rffi.ptradd(storage, index))[0] = item

def free_raw_storage(storage):
    lltype.free(storage, flavor='raw')

class RawStorageSetitemEntry(ExtRegistryEntry):
    _about_ = raw_storage_setitem

    def compute_result_annotation(self, s_storage, s_index, s_item):
        assert annmodel.SomeInteger().contains(s_index)

    def specialize_call(self, hop):
        assert not lltype_is_gc(hop.args_r[2].lowleveltype)
        assert hop.args_r[0].lowleveltype == RAW_STORAGE_PTR
        v_storage, v_index, v_item = hop.inputargs(hop.args_r[0],
                                                   lltype.Signed,
                                                   hop.args_r[2])
        c_typ = hop.inputconst(lltype.Void, hop.args_r[2].lowleveltype)
        hop.exception_cannot_occur()
        v_addr = hop.genop('cast_ptr_to_adr', [v_storage],
                           resulttype=llmemory.Address)
        return hop.genop('raw_store', [v_addr, c_typ, v_index, v_item])
