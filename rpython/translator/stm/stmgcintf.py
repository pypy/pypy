import py, os
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.conftest import cdir as cdir2


cdir = os.path.abspath(os.path.join(cdir2, '..', 'stm'))

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    includes = ['src_stm/stmgc.h'],
    pre_include_bits = ['#define PYPY_LONG_BIT %d' % LONG_BIT,
                        '#define RPY_STM 1'],
)

def _llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           _nowrapper=True, transactionsafe=True,
                           **kwds)

def smexternal(name, args, result):
    return staticmethod(_llexternal(name, args, result))

# ____________________________________________________________


class StmOperations(object):

    CALLBACK_TX     = lltype.Ptr(lltype.FuncType([rffi.VOIDP, lltype.Signed],
                                                 lltype.Signed))
    DUPLICATE       = lltype.Ptr(lltype.FuncType([llmemory.Address],
                                                 llmemory.Address))
    CALLBACK_ENUM   = lltype.Ptr(lltype.FuncType([llmemory.Address]*2,
                                                 lltype.Void))

    def _freeze_(self):
        return True

    # C part of the implementation of the pypy.rlib.rstm module
    in_transaction = smexternal('stm_in_transaction', [], lltype.Signed)
    is_inevitable = smexternal('stm_is_inevitable', [], lltype.Signed)
    should_break_transaction = smexternal('stm_should_break_transaction',
                                          [], lltype.Signed)
    add_atomic = smexternal('stm_add_atomic', [lltype.Signed], lltype.Void)
    get_atomic = smexternal('stm_get_atomic', [], lltype.Signed)
    descriptor_init = smexternal('DescriptorInit', [], lltype.Signed)
    descriptor_done = smexternal('DescriptorDone', [], lltype.Void)
    begin_inevitable_transaction = smexternal(
        'BeginInevitableTransaction', [], lltype.Void)
    commit_transaction = smexternal(
        'CommitTransaction', [], lltype.Void)
    perform_transaction = smexternal('stm_perform_transaction',
                                     [CALLBACK_TX, rffi.VOIDP, llmemory.Address],
                                     lltype.Void)

    # for the GC: store and read a thread-local-storage field
    set_tls = smexternal('stm_set_tls', [llmemory.Address], llmemory.Address)
    get_tls = smexternal('stm_get_tls', [], llmemory.Address)
    del_tls = smexternal('stm_del_tls', [], lltype.Void)

    # calls FindRootsForLocalCollect() and invokes for each such root
    # the callback set in CALLBACK_ENUM.
    tldict_enum = smexternal('stm_tldict_enum', [], lltype.Void)
    tldict_enum_external = smexternal('stm_tldict_enum_external',
                                      [llmemory.Address], lltype.Void)

    # sets the transaction length, after which should_break_transaction()
    # returns True
    set_transaction_length = smexternal('stm_set_transaction_length',
                                        [lltype.Signed], lltype.Void)

    abort_info_pop = smexternal('stm_abort_info_pop',
                                [lltype.Signed], lltype.Void)
    inspect_abort_info = smexternal('stm_inspect_abort_info',
                                    [], rffi.CCHARP)

    start_single_thread = smexternal('stm_start_single_thread',[], lltype.Void)
    stop_single_thread  = smexternal('stm_stop_single_thread', [], lltype.Void)

    # for testing
    abort_and_retry = smexternal('stm_abort_and_retry', [], lltype.Void)
