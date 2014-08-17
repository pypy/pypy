from rpython.rtyper.lltypesystem import lltype, lloperation, rclass
from rpython.translator.stm.support import is_immutable
from rpython.flowspace.model import SpaceOperation, Constant
from rpython.translator.unsimplify import varoftype


ALWAYS_ALLOW_OPERATIONS = set([
    'force_cast', 'keepalive', 'cast_ptr_to_adr',
    'cast_adr_to_int',
    'debug_print', 'debug_assert',
    'debug_start', 'debug_stop', 'have_debug_prints',
    'cast_opaque_ptr', 'hint',
    'stack_current', 'gc_stack_bottom', 'cast_ptr_to_int',
    'jit_force_virtual', 'jit_force_virtualizable',
    'jit_force_quasi_immutable', 'jit_marker', 'jit_is_virtual',
    'jit_record_known_class',
    'gc_identityhash', 'gc_id', 'gc_can_move', 'gc__collect',
    'gc_adr_of_root_stack_top', 'gc_add_memory_pressure',
    'weakref_create', 'weakref_deref',
    'jit_assembler_call', 'gc_writebarrier',
    'shrink_array',
    'threadlocalref_get', 'threadlocalref_set',
    ])
ALWAYS_ALLOW_OPERATIONS |= set(lloperation.enum_tryfold_ops())

for opname, opdesc in lloperation.LL_OPERATIONS.iteritems():
    if opname.startswith('stm_'):
        ALWAYS_ALLOW_OPERATIONS.add(opname)

GETTERS = set(['getfield', 'getarrayitem', 'getinteriorfield', 'raw_load'])
SETTERS = set(['setfield', 'setarrayitem', 'setinteriorfield', 'raw_store'])
MALLOCS = set(['malloc', 'malloc_varsize',
               'malloc_nonmovable', 'malloc_nonmovable_varsize',
               'raw_malloc',
               'do_malloc_fixedsize_clear', 'do_malloc_varsize_clear'])
FREES   = set(['free', 'raw_free'])

# ____________________________________________________________

def should_turn_inevitable_getter_setter(op, fresh_mallocs):
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
    return not fresh_mallocs.is_fresh_malloc(op.args[0])

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


def should_turn_inevitable(op, block, fresh_mallocs):
    # Always-allowed operations never cause a 'turn inevitable'
    if op.opname in ALWAYS_ALLOW_OPERATIONS:
        return False
    #
    # Getters and setters
    if op.opname in GETTERS:
        if op.result.concretetype is lltype.Void:
            return False
        return should_turn_inevitable_getter_setter(op, fresh_mallocs)
    if op.opname in SETTERS:
        if op.args[-1].concretetype is lltype.Void:
            return False
        return should_turn_inevitable_getter_setter(op, fresh_mallocs)
    #
    # Mallocs & Frees
    if op.opname in MALLOCS:
        return False
    if op.opname in FREES:
        # We can only run a CFG in non-inevitable mode from start
        # to end in one transaction (every free gets called once
        # for every fresh malloc). No need to turn inevitable.
        # If the transaction is splitted, the remaining parts of the
        # CFG will always run in inevitable mode anyways.
        return not fresh_mallocs.is_fresh_malloc(op.args[0])
    #
    # Function calls
    if op.opname == 'direct_call' or op.opname == 'indirect_call':
        return should_turn_inevitable_call(op)
    #
    # Entirely unsupported operations cause a 'turn inevitable'
    return True


def turn_inevitable_op(info):
    c_info = Constant(info, lltype.Void)
    return SpaceOperation('stm_become_inevitable', [c_info],
                          varoftype(lltype.Void))

def insert_turn_inevitable(graph):
    from rpython.translator.backendopt.writeanalyze import FreshMallocs
    fresh_mallocs = FreshMallocs(graph)
    for block in graph.iterblocks():
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            inev = should_turn_inevitable(op, block, fresh_mallocs)
            if inev:
                if not isinstance(inev, str):
                    inev = op.opname
                inev_op = turn_inevitable_op(inev)
                block.operations.insert(i, inev_op)
