
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.annotator import model as annmodel
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.rlib.rgc import lltype_is_gc
from rpython.rlib.objectmodel import specialize

RAW_STORAGE = rffi.CCHARP.TO
RAW_STORAGE_PTR = rffi.CCHARP

@specialize.arg(1, 2)
def alloc_raw_storage(size, track_allocation=True, zero=False):
    return lltype.malloc(RAW_STORAGE, size, flavor='raw',
                         add_memory_pressure=True,
                         track_allocation=track_allocation,
                         zero=zero)

def raw_storage_getitem(TP, storage, index):
    "NOT_RPYTHON"
    return rffi.cast(rffi.CArrayPtr(TP), rffi.ptradd(storage, index))[0]

def raw_storage_setitem(storage, index, item):
    "NOT_RPYTHON"
    TP = rffi.CArrayPtr(lltype.typeOf(item))
    rffi.cast(TP, rffi.ptradd(storage, index))[0] = item

@specialize.arg(1)
def free_raw_storage(storage, track_allocation=True):
    lltype.free(storage, flavor='raw', track_allocation=track_allocation)

class RawStorageGetitemEntry(ExtRegistryEntry):
    _about_ = raw_storage_getitem

    def compute_result_annotation(self, s_TP, s_storage, s_index):
        assert s_TP.is_constant()
        return lltype_to_annotation(s_TP.const)

    def specialize_call(self, hop):
        assert hop.args_r[1].lowleveltype == RAW_STORAGE_PTR
        v_storage = hop.inputarg(hop.args_r[1], arg=1)
        v_index   = hop.inputarg(lltype.Signed, arg=2)
        hop.exception_cannot_occur()
        v_addr = hop.genop('cast_ptr_to_adr', [v_storage],
                           resulttype=llmemory.Address)
        return hop.genop('raw_load', [v_addr, v_index],
                         resulttype=hop.r_result.lowleveltype)

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
        hop.exception_cannot_occur()
        v_addr = hop.genop('cast_ptr_to_adr', [v_storage],
                           resulttype=llmemory.Address)
        return hop.genop('raw_store', [v_addr, v_index, v_item])
