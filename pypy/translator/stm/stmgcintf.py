from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gc.stmgc import PRIMITIVE_SIZES
from pypy.translator.stm import _rffi_stm


def smexternal(name, args, result):
    return staticmethod(_rffi_stm.llexternal(name, args, result))

CALLBACK = lltype.Ptr(lltype.FuncType([llmemory.Address] * 2, lltype.Void))
GETSIZE  = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Signed))


class StmOperations(object):

    def _freeze_(self):
        return True

    setup_size_getter = smexternal('stm_setup_size_getter', [GETSIZE],
                                   lltype.Void)

    set_tls = smexternal('stm_set_tls', [llmemory.Address, lltype.Signed],
                         lltype.Void)
    get_tls = smexternal('stm_get_tls', [], llmemory.Address)
    del_tls = smexternal('stm_del_tls', [], lltype.Void)

    tldict_lookup = smexternal('stm_tldict_lookup', [llmemory.Address],
                               llmemory.Address)
    tldict_add = smexternal('stm_tldict_add', [llmemory.Address] * 2,
                            lltype.Void)
    tldict_enum = smexternal('stm_tldict_enum', [CALLBACK], lltype.Void)

    for _size, _TYPE in PRIMITIVE_SIZES.items():
        _name = 'stm_read_int%d' % _size
        locals()[_name] = smexternal(_name, [llmemory.Address, lltype.Signed],
                                     _TYPE)

    stm_copy_transactional_to_raw = smexternal('stm_copy_transactional_to_raw',
                                               [llmemory.Address,
                                                llmemory.Address,
                                                lltype.Signed],
                                               lltype.Void)
