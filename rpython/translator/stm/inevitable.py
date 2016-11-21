from rpython.rtyper.lltypesystem import lltype, lloperation
from rpython.rtyper import rclass
from rpython.translator.stm.support import is_immutable
from rpython.flowspace.model import SpaceOperation, Constant
from rpython.translator.unsimplify import varoftype
from rpython.translator.backendopt.dataflow import AbstractForwardDataFlowAnalysis
from rpython.translator.backendopt.support import var_needsgc
from rpython.translator.simplify import join_blocks

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
    'threadlocalref_acquire', 'threadlocalref_enum', 'threadlocalref_release',
    'jit_enter_portal_frame', 'jit_leave_portal_frame',

    'gc_fq_next_dead', # -> stm_next_to_finalize()
    'gc_fq_register', # -> stm_register_finalizer()
    ])
ALWAYS_ALLOW_OPERATIONS |= set(lloperation.enum_tryfold_ops())

for opname, opdesc in lloperation.LL_OPERATIONS.iteritems():
    if opname.startswith('stm_'):
        ALWAYS_ALLOW_OPERATIONS.add(opname)

CALLS   = set(['direct_call', 'indirect_call'])
GETTERS = set(['getfield', 'getarrayitem', 'getinteriorfield', 'raw_load',
               'gc_load_indexed'])
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
    'gc_rawrefcount_from_obj', 'gc_rawrefcount_init',
    'gc_rawrefcount_create_link_pyobj', 'gc_rawrefcount_create_link_pypy',
    'gc_rawrefcount_to_obj',
    'gc_bit',
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


def should_turn_inevitable(op, fresh_vars=set()):
    # Always-allowed operations never cause a 'turn inevitable'
    if op.opname in ALWAYS_ALLOW_OPERATIONS:
        return False
    assert op.opname not in INCOMPATIBLE_OPS, repr(op)
    #
    # Getters and setters
    if op.opname in GETTERS:
        if op.result.concretetype is lltype.Void:
            return False
        elif op.args[0] in fresh_vars:
            return False
        return should_turn_inevitable_getter_setter(op)
    if op.opname in SETTERS:
        if op.args[-1].concretetype is lltype.Void:
            return False
        elif op.args[0] in fresh_vars:
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


class InevitableAnalysis(AbstractForwardDataFlowAnalysis):
    """Determines the exact set of operations that need
    to turn a transaction inevitable.
    * Inevitable transactions can only be interrupted by
      possible transaction breaks. Otherwise, repeated
      turn_inevitables are superfluous.
    * Raw-writes to freshly allocated memory are safe,
      as the memory will be freed on abort."""

    def __init__(self, break_analyzer):
        self.break_analyzer = break_analyzer
        self.in_stm_ignored = False
        self.turn_inevitable_ops = set()

    def entry_state(self, block):
        return (False, # not inevitable
                set()) # no freshly allocated vars

    def initialize_block(self, block):
        # the initial out_state of a block is that
        # all raw variables are "freshly allocated". This is the
        # "neutral element" for the join_operation
        out_state = set()
        for link in block.exits:
            for arg in link.args:
                if not var_needsgc(arg):
                    out_state.add(arg)
        return (True, out_state)

    def join_operation(self, inputargs, preds_outs, links_to_preds):
        fresh_vars = set(inputargs)
        for i, iarg in enumerate(inputargs):
            # check in all predecessory if the iarg was
            # fresh there
            for pidx, pouts in enumerate(preds_outs):
                name_in_pred = links_to_preds[pidx].args[i]
                if name_in_pred not in pouts[1]:
                    # not fresh in pred[pidx]
                    fresh_vars.remove(iarg)
                    break
        #
        return (all([p[0] for p in preds_outs]), fresh_vars)

    def transfer_function(self, block, in_state):
        assert not self.in_stm_ignored
        inevitable, fresh_vars = in_state[0], set(in_state[1])
        #
        for op in block.operations:
            if op.opname == "stm_ignored_start":
                assert not self.in_stm_ignored
                self.in_stm_ignored = True
            elif op.opname == "stm_ignored_stop":
                assert self.in_stm_ignored
                self.in_stm_ignored = False
            elif op.opname in ("cast_pointer", "same_as"):
                if op.args[0] in fresh_vars:
                    fresh_vars.add(op.result)
            elif op.opname in MALLOCS and not var_needsgc(op.result):
                fresh_vars.add(op.result)
            #
            if inevitable:
                if op in self.turn_inevitable_ops:
                    # remove if considered unsafe previously
                    # (can probably never happen)
                    self.turn_inevitable_ops.remove(op)
            elif not self.in_stm_ignored and should_turn_inevitable(op, fresh_vars):
                self.turn_inevitable_ops.add(op)
                inevitable = True
            elif op.opname == 'stm_become_inevitable':
                inevitable = True
            else:
                assert op not in self.turn_inevitable_ops
            #
            # check breaking ops here to be safe (e.g. if there
            # was an op that turns inevitable, but also breaks)
            if self.break_analyzer.analyze(op):
                inevitable = False
                # breaks also always clear fresh_vars
                fresh_vars.clear()
        #
        return (inevitable, fresh_vars)


    def calculate(self, graph, entrymap=None):
        assert not self.in_stm_ignored
        assert not self.turn_inevitable_ops
        return super(InevitableAnalysis, self).calculate(graph, entrymap)


def turn_inevitable_op(info):
    c_info = Constant(info, lltype.Void)
    return SpaceOperation('stm_become_inevitable', [c_info],
                          varoftype(lltype.Void))

def insert_turn_inevitable(stmtransformer, graph):
    # needed for cases where stm_ignored_stop is in its own block:
    join_blocks(graph)

    ia = InevitableAnalysis(stmtransformer.break_analyzer)
    ia.calculate(graph)
    #
    for block in graph.iterblocks():
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op in ia.turn_inevitable_ops:
                why = should_turn_inevitable(op)
                if not isinstance(why, str):
                    why = op.opname
                inev_op = turn_inevitable_op(why)
                block.operations.insert(i, inev_op)
