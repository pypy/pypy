import re
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython.lltypesystem import rclass
from pypy.tool.pairtype import pair, pairtype
from pypy.rlib.objectmodel import we_are_translated

def fixupobj(EXPECTED_TYPE, x):
    if isinstance(EXPECTED_TYPE, lltype.Ptr):
        if lltype.typeOf(x) == llmemory.GCREF:
            if x is None:
                return lltype.nullptr(EXPECTED_TYPE.TO)
            x = lltype.cast_opaque_ptr(EXPECTED_TYPE, x)
        else:
            x = x._as_ptr()
        return lltype.cast_pointer(EXPECTED_TYPE, x)
    #elif isinstance(EXPECTED_TYPE, ootype.Instance):
    #    x = realobj(x)
    #    return ootype._view(EXPECTED_TYPE, x)
    elif EXPECTED_TYPE is lltype.Void:
        return x
    else:
        return lltype.cast_primitive(EXPECTED_TYPE, x)

def cast_vable(p):
    T = lltype.Ptr(lltype.typeOf(p._obj.container))
    p = lltype.cast_opaque_ptr(T, p)
    STRUCT = cast_vable_type(T.TO)
    return lltype.cast_pointer(lltype.Ptr(STRUCT), p)

def cast_vable_type(STRUCT):
    assert STRUCT._hints.get('virtualizable2'), \
           "not a virtualizable2: %r" % (p,)
    while True:
        _, PARENT = STRUCT._first_struct()
        if PARENT is None or not PARENT._hints.get('virtualizable2'):
            break
        STRUCT = PARENT
    return STRUCT

def get_vtable_for_gcstruct(cpu, GCSTRUCT):
    # xxx hack: from a GcStruct representing an instance's
    # lowleveltype, return the corresponding vtable pointer.
    # Returns None if the GcStruct does not belong to an instance.
    assert isinstance(GCSTRUCT, lltype.GcStruct)
    HEAD = GCSTRUCT
    while not HEAD._hints.get('typeptr'):
        _, HEAD = HEAD._first_struct()
        if HEAD is None:
            return None
    setup_cache_gcstruct2vtable(cpu)
    return cpu._cache_gcstruct2vtable[GCSTRUCT]

def setup_cache_gcstruct2vtable(cpu):
    if not hasattr(cpu, '_cache_gcstruct2vtable'):
        cache = {}
        cache.update(testing_gcstruct2vtable)
        for rinstance in cpu.rtyper.instance_reprs.values():
            cache[rinstance.lowleveltype.TO] = rinstance.rclass.getvtable()
        cpu._cache_gcstruct2vtable = cache

def set_testing_vtable_for_gcstruct(GCSTRUCT, vtable):
    # only for tests that need to register the vtable of their malloc'ed
    # structures in case they are GcStruct inheriting from OBJECT.
    testing_gcstruct2vtable[GCSTRUCT] = vtable

def populate_type_cache(graphs, cpu):
    cache = {}
    for graph in graphs:
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'malloc':
                    STRUCT = op.args[0].value
                    if isinstance(STRUCT, lltype.GcStruct):
                        vtable = get_vtable_for_gcstruct(cpu, STRUCT)
                        if vtable:
                            vt = cpu.cast_adr_to_int(
                                llmemory.cast_ptr_to_adr(vtable))
                            cache[vt] = cpu.sizeof(STRUCT)
    return cache

testing_gcstruct2vtable = {}

# ____________________________________________________________
# helpers

def setup():
    for _opname, _opdesc in lloperation.LL_OPERATIONS.iteritems():
        if _opdesc.canfold:
            always_pure_operations[_opname] = None
        if not _opdesc.sideeffects:
            operations_without_side_effects[_opname] = None
        if not _opdesc.canraise:
            operation_never_raises[_opname] = None

    # XXX fish fish fish
    operations_without_side_effects['getfield_gc'] = None

operations_without_side_effects = {}
always_pure_operations = {}
operation_never_raises = {}

for guard in ['guard_no_exception', 'guard_true',
              'guard_false', 'guard_value', 'guard_class']:
    always_pure_operations[guard] = None
    operation_never_raises[guard] = None

setup()
