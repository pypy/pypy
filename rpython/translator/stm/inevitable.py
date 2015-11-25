from rpython.rtyper.lltypesystem import lltype, lloperation
from rpython.rtyper import rclass
from rpython.translator.stm.support import is_immutable
from rpython.flowspace.model import SpaceOperation, Constant
from rpython.translator.unsimplify import varoftype


ALWAYS_ALLOW_OPERATIONS = set([
    'force_cast', 'keepalive', 'cast_ptr_to_adr',
    'cast_adr_to_int', 'cast_int_to_ptr',
    'cast_ptr_to_weakrefptr', 'cast_weakrefptr_to_ptr',
    'debug_print', 'debug_assert', 'debug_flush', 'debug_offset',
    'debug_start', 'debug_stop', 'have_debug_prints',
    'have_debug_prints_for',
    'debug_catch_exception', 'debug_nonnull_pointer',
    'debug_record_traceback', 'debug_start_traceback',
    'debug_reraise_traceback',
    'cast_opaque_ptr', 'hint',
    'stack_current', 'gc_stack_bottom', 'cast_ptr_to_int',
    'jit_force_virtual', 'jit_force_virtualizable',
    'jit_force_quasi_immutable', 'jit_marker', 'jit_is_virtual',
    'jit_record_exact_class', 'jit_ffi_save_result',
    'gc_identityhash', 'gc_id', 'gc_can_move', 'gc__collect',
    'gc_adr_of_root_stack_top', 'gc_add_memory_pressure',
    'gc_pin', 'gc_unpin', 'gc__is_pinned',
    'weakref_create', 'weakref_deref',
    'jit_assembler_call', 'gc_writebarrier',
    'shrink_array',
    'threadlocalref_addr', 'threadlocalref_get',
    'gc_get_rpy_memory_usage', 'gc_get_rpy_referents',
    'gc_get_rpy_roots', 'gc_get_rpy_type_index', 'gc_get_type_info_group',
    'gc_heap_stats', 'gc_is_rpy_instance', 'gc_typeids_list',
    'gc_typeids_z', 'gc_gettypeid', 'nop',
    'length_of_simple_gcarray_from_opaque',
    'll_read_timestamp',
    'jit_conditional_call',
    'get_exc_value_addr', 'get_exception_addr',
    'get_write_barrier_failing_case',
    'get_write_barrier_from_array_failing_case',
    'gc_set_max_heap_size', 'gc_gcflag_extra',
    'raw_malloc_usage',
    'track_alloc_start', 'track_alloc_stop',
    ])
ALWAYS_ALLOW_OPERATIONS |= set(lloperation.enum_tryfold_ops())

for opname, opdesc in lloperation.LL_OPERATIONS.iteritems():
    if opname.startswith('stm_'):
        ALWAYS_ALLOW_OPERATIONS.add(opname)

CALLS   = set(['direct_call', 'indirect_call'])
GETTERS = set(['getfield', 'getarrayitem', 'getinteriorfield', 'raw_load'])
SETTERS = set(['setfield', 'setarrayitem', 'setinteriorfield', 'raw_store'])
MALLOCS = set(['malloc', 'malloc_varsize',
               'raw_malloc',
               'do_malloc_fixedsize', 'do_malloc_varsize',
               'do_malloc_fixedsize_clear', 'do_malloc_varsize_clear'])
FREES   = set(['free', 'raw_free'])

# These operations should not appear at all in an stm build at the
# point this file is invoked (before gctransform)
INCOMPATIBLE_OPS = set([
    'bare_raw_store', 'bare_setarrayitem', 'bare_setfield',
    'bare_setinteriorfield',
    'boehm_disappearing_link', 'boehm_malloc', 'boehm_malloc_atomic',
    'boehm_register_finalizer',
    'check_and_clear_exc', 'check_no_more_arg', 'check_self_nonzero',
    'debug_stm_flush_barrier', 'debug_view',
    'decode_arg', 'decode_arg_def',
    'gc_adr_of_nursery_free', 'gc_adr_of_nursery_top',
    'gc_adr_of_root_stack_base', 'gc_asmgcroot_static',
    'gc_call_rtti_destructor', 'gc_deallocate',
    'gc_detach_callback_pieces', 'gc_fetch_exception',
    'gc_free',
    'gc_obtain_free_space',
    'gc_reattach_callback_pieces', 'gc_reload_possibly_moved',
    'gc_restore_exception',
    'gc_thread_run',
    'gc_writebarrier_before_copy',
    'getslice', 'instrument_count',
    'stack_malloc',
    'zero_gc_pointers_inside',
    ])

# These operations always turn the transaction inevitable.
TURN_INEVITABLE_OPS = set([
    'debug_fatalerror', 'debug_llinterpcall', 'debug_print_traceback',
    'gc_dump_rpy_heap', 'gc_thread_start', 'gc_thread_die',
    'raw_memclear', 'raw_memcopy', 'raw_memmove', 'raw_memset',
    'gc_thread_after_fork', 'gc_thread_before_fork',
    'debug_forked',
    ])

# ____________________________________________________________

def should_turn_inevitable_getter_setter(op):
    # Getters and setters are allowed if their first argument is a GC pointer.
    # If it is a RAW pointer, and it is a read from a non-immutable place,
    # and it doesn't use the hint 'stm_dont_track_raw_accesses', then they
    # turn inevitable.
    TYPE = op.args[0].concretetype
    if is_immutable(op):
        return False
    if not isinstance(TYPE, lltype.Ptr):
        return True     # raw_load or raw_store with a number or address
    S = TYPE.TO
    if S._gckind == 'gc':
        return False
    if S._hints.get('stm_dont_track_raw_accesses', False):
        return False
    return True

def should_turn_inevitable_call(op):
    if op.opname == 'direct_call':
        funcptr = op.args[0].value._obj
        if not hasattr(funcptr, "external"):
            return False
        if getattr(funcptr, "transactionsafe", False):
            return False
        try:
            return funcptr._name + '()'
        except AttributeError:
            return True

    elif op.opname == 'indirect_call':
        tographs = op.args[-1].value
        if tographs is not None:
            # Set of RPython functions
            return False
        # unknown function
        return True

    assert False


def should_turn_inevitable(op, block):
    # Always-allowed operations never cause a 'turn inevitable'
    if op.opname in ALWAYS_ALLOW_OPERATIONS:
        return False
    assert op.opname not in INCOMPATIBLE_OPS, repr(op)
    #
    # Getters and setters
    if op.opname in GETTERS:
        if op.result.concretetype is lltype.Void:
            return False
        return should_turn_inevitable_getter_setter(op)
    if op.opname in SETTERS:
        if op.args[-1].concretetype is lltype.Void:
            return False
        return should_turn_inevitable_getter_setter(op)
    #
    # Mallocs & Frees
    if op.opname in MALLOCS:
        return False
    if op.opname in FREES:
        return False
    #
    # Function calls
    if op.opname in CALLS:
        return should_turn_inevitable_call(op)
    #
    # Entirely unsupported operations cause a 'turn inevitable'
    return True


def turn_inevitable_op(info):
    c_info = Constant(info, lltype.Void)
    return SpaceOperation('stm_become_inevitable', [c_info],
                          varoftype(lltype.Void))

def insert_turn_inevitable(graph):
    for block in graph.iterblocks():
        stm_ignored = False
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            inev = should_turn_inevitable(op, block)
            if inev and not stm_ignored:
                if not isinstance(inev, str):
                    inev = op.opname
                inev_op = turn_inevitable_op(inev)
                block.operations.insert(i, inev_op)
            if op.opname == 'stm_ignored_stop':
                assert not stm_ignored, "nested stm_ignored_stop"
                stm_ignored = True      # backward, so "stop" enables it
            elif op.opname == 'stm_ignored_start':
                if not stm_ignored:
                    raise Exception("%r: 'with stm_ignored: stm_ignored start "
                                    "without end in the same block" % (graph,))
                stm_ignored = False     # backward, so "start" disables it
        if stm_ignored:
            raise Exception("%r: 'with stm_ignored:' code body too complex"
                            % (graph,))
