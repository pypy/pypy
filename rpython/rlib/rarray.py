from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.extregistry import ExtRegistryEntry

def copy_list_to_raw_array(lst, array):
    for i, item in enumerate(lst):
        array[i] = item

        
class Entry(ExtRegistryEntry):
    _about_ = copy_list_to_raw_array

    def compute_result_annotation(self, *s_args):
        pass

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        v_list, v_buf = hop.inputargs(*hop.args_r)
        return hop.gendirectcall(ll_copy_list_to_raw_array, v_list, v_buf)


def ll_copy_list_to_raw_array(ll_list, dst_ptr):
    src_ptr = ll_list.ll_items()
    src_adr = llmemory.cast_ptr_to_adr(src_ptr)
    src_adr += llmemory.itemoffsetof(lltype.typeOf(src_ptr).TO, 0) # skip the GC header
    #
    dst_adr = llmemory.cast_ptr_to_adr(dst_ptr)
    dst_adr += llmemory.itemoffsetof(lltype.typeOf(dst_ptr).TO, 0)
    #
    ITEM = lltype.typeOf(dst_ptr).TO.OF
    size = llmemory.sizeof(ITEM) * ll_list.ll_length()
    llmemory.raw_memcopy(src_adr, dst_adr, size)
