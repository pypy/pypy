import py
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rarithmetic import LONG_BIT


cdir = py.path.local(pypydir) / 'translator' / 'stm'
cdir2 = py.path.local(pypydir) / 'translator' / 'c'

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    includes = ['src_stm/et.h', 'src_stm/et.c'],
    pre_include_bits = ['#define PYPY_LONG_BIT %d' % LONG_BIT,
                        '#define RPY_STM 1'],
    separate_module_sources = ['\n'],    # hack for test_rffi_stm
)

def _llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           _nowrapper=True, **kwds)

def smexternal(name, args, result):
    return staticmethod(_llexternal(name, args, result))

# ____________________________________________________________


class StmOperations(object):

    PRIMITIVE_SIZES   = {1: lltype.Char,
                         2: rffi.SHORT,
                         4: rffi.INT,
                         8: lltype.SignedLongLong,
                         '8f': rffi.DOUBLE,
                         '4f': rffi.FLOAT}

    CALLBACK_TX   = lltype.Ptr(lltype.FuncType([rffi.VOIDP, lltype.Signed],
                                               rffi.VOIDP))
    CALLBACK_ENUM = lltype.Ptr(lltype.FuncType([llmemory.Address] * 3,
                                               lltype.Void))
    GETSIZE  = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Signed))

    def _freeze_(self):
        return True

    setup_size_getter = smexternal('stm_setup_size_getter', [GETSIZE],
                                   lltype.Void)

    in_transaction = smexternal('stm_in_transaction', [], lltype.Signed)
    _activate_transaction = smexternal('_stm_activate_transaction',
                                       [lltype.Signed], lltype.Void)

    set_tls = smexternal('stm_set_tls', [llmemory.Address, lltype.Signed],
                         lltype.Void)
    get_tls = smexternal('stm_get_tls', [], llmemory.Address)
    del_tls = smexternal('stm_del_tls', [], lltype.Void)

    tldict_lookup = smexternal('stm_tldict_lookup', [llmemory.Address],
                               llmemory.Address)
    tldict_add = smexternal('stm_tldict_add', [llmemory.Address] * 2,
                            lltype.Void)
    tldict_enum = smexternal('stm_tldict_enum', [CALLBACK_ENUM], lltype.Void)

    for _size, _TYPE in PRIMITIVE_SIZES.items():
        _name = 'stm_read_int%s' % _size
        locals()[_name] = smexternal(_name, [llmemory.Address, lltype.Signed],
                                     _TYPE)

    stm_copy_transactional_to_raw = smexternal('stm_copy_transactional_to_raw',
                                               [llmemory.Address,
                                                llmemory.Address,
                                                lltype.Signed],
                                               lltype.Void)

    try_inevitable = smexternal('stm_try_inevitable', [], lltype.Void)
    perform_transaction = smexternal('stm_perform_transaction',
                                     [CALLBACK_TX, rffi.VOIDP], rffi.VOIDP)
    thread_id        = smexternal('stm_thread_id',       [], lltype.Signed)
    abort_and_retry  = smexternal('stm_abort_and_retry', [], lltype.Void)

    _debug_get_state = smexternal('stm_debug_get_state', [], lltype.Signed)
    STATE_NOT_INITIALIZED   = -2
    STATE_MAIN_THREAD       = -1
    STATE_INACTIVE          = 0
    STATE_ACTIVE            = 1
    STATE_ACTIVE_INEVITABLE = 2
