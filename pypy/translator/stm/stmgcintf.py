import py
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rarithmetic import LONG_BIT


cdir = py.path.local(pypydir) / 'translator' / 'stm'
cdir2 = py.path.local(pypydir) / 'translator' / 'c'

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    includes = ['src_stm/et.h'],
    pre_include_bits = ['#define PYPY_LONG_BIT %d' % LONG_BIT,
                        '#define RPY_STM 1'],
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

    INIT_DONE       = lltype.Ptr(lltype.FuncType([], lltype.Void))
    RUN_TRANSACTION = lltype.Ptr(lltype.FuncType([rffi.VOIDP, lltype.Signed],
                                                 rffi.VOIDP))
    GETSIZE         = lltype.Ptr(lltype.FuncType([llmemory.Address],
                                                 lltype.Signed))
    CALLBACK_ENUM   = lltype.Ptr(lltype.FuncType([llmemory.Address]*3,
                                                 lltype.Void))

    def _freeze_(self):
        return True

    # C part of the implementation of the pypy.rlib.rstm module
    in_transaction = smexternal('stm_in_transaction', [], lltype.Signed)
    is_inevitable = smexternal('stm_is_inevitable', [], lltype.Signed)
    begin_inevitable_transaction = smexternal(
        'stm_begin_inevitable_transaction', [], lltype.Void)
    commit_transaction = smexternal(
        'stm_commit_transaction', [], lltype.Void)
    do_yield_thread = smexternal('stm_do_yield_thread',
                                 [], lltype.Void)

    # for the GC: store and read a thread-local-storage field, as well
    # as initialize and shut down the internal thread_descriptor
    set_tls = smexternal('stm_set_tls', [llmemory.Address], lltype.Void)
    get_tls = smexternal('stm_get_tls', [], llmemory.Address)
    del_tls = smexternal('stm_del_tls', [], lltype.Void)

    # return the current thread id (a random non-null number, or 0 for
    # the main thread)
    thread_id = smexternal('stm_thread_id', [], lltype.Signed)

    # lookup, add, and enumerate the content of the internal dictionary
    # that maps GLOBAL objects to LOCAL objects
    tldict_lookup = smexternal('stm_tldict_lookup', [llmemory.Address],
                               llmemory.Address)
    tldict_add = smexternal('stm_tldict_add', [llmemory.Address] * 2,
                            lltype.Void)
    tldict_enum = smexternal('stm_tldict_enum', [], lltype.Void)

    # reader functions, to call if the object is GLOBAL
    for _size, _TYPE in PRIMITIVE_SIZES.items():
        _name = 'stm_read_int%s' % _size
        locals()[_name] = smexternal(_name, [llmemory.Address, lltype.Signed],
                                     _TYPE)

    # a special reader function that copies all the content of the object
    # somewhere else
    stm_copy_transactional_to_raw = smexternal('stm_copy_transactional_to_raw',
                                               [llmemory.Address,
                                                llmemory.Address,
                                                lltype.Signed],
                                               lltype.Void)

    # if running in a transaction, make it inevitable
    try_inevitable = smexternal('stm_try_inevitable', [], lltype.Void)

    # for testing
    abort_and_retry  = smexternal('stm_abort_and_retry', [], lltype.Void)
