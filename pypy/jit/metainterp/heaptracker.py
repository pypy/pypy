import re
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython.ootypesystem import ootype
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
    T = lltype.Ptr(lltype.typeOf(p._obj._normalizedcontainer()))
    p = lltype.cast_opaque_ptr(T, p)
    STRUCT = cast_vable_type(T.TO)
    return lltype.cast_pointer(lltype.Ptr(STRUCT), p)

def cast_vable_type(STRUCT_OR_INST):
    if isinstance(STRUCT_OR_INST, ootype.Instance):
        return cast_vable_type_instance(STRUCT_OR_INST)
    else:
        return cast_vable_type_struct(STRUCT_OR_INST)

def cast_vable_type_struct(STRUCT):
    assert STRUCT._hints.get('virtualizable2'), \
           "not a virtualizable2: %r" % (STRUCT,)
    while True:
        _, PARENT = STRUCT._first_struct()
        if PARENT is None or not PARENT._hints.get('virtualizable2'):
            break
        STRUCT = PARENT
    return STRUCT

def cast_vable_type_instance(INSTANCE):
    assert INSTANCE._hints.get('virtualizable2'), \
           "not a virtualizable2: %r" % (INSTANCE,)
    while True:
        PARENT = INSTANCE._superclass
        if PARENT is None or not PARENT._hints.get('virtualizable2'):
            break
        INSTANCE = PARENT
    return INSTANCE


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

def set_testing_vtable_for_gcstruct(GCSTRUCT, vtable, name):
    # only for tests that need to register the vtable of their malloc'ed
    # structures in case they are GcStruct inheriting from OBJECT.
    namez = name + '\x00'
    vtable.name = lltype.malloc(rclass.OBJECT_VTABLE.name.TO, len(namez),
                                immortal=True)
    for i in range(len(namez)):
        vtable.name[i] = namez[i]
    testing_gcstruct2vtable[GCSTRUCT] = vtable

testing_gcstruct2vtable = {}
