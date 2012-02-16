from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rlib.objectmodel import we_are_translated


def adr2int(addr):
    # Cast an address to an int.  Returns an AddressAsInt object which
    # can be cast back to an address.
    return llmemory.cast_adr_to_int(addr, "symbolic")

def int2adr(int):
    return llmemory.cast_int_to_adr(int)

def count_fields_if_immutable(STRUCT):
    assert isinstance(STRUCT, lltype.GcStruct)
    if STRUCT._hints.get('immutable', False):
        try:
            return _count_fields(STRUCT)
        except ValueError:
            pass
    return -1

def _count_fields(STRUCT):
    if STRUCT == rclass.OBJECT:
        return 0    # don't count 'typeptr'
    result = 0
    for fieldname, TYPE in STRUCT._flds.items():
        if TYPE is lltype.Void:
            pass       # ignore Voids
        elif not isinstance(TYPE, lltype.ContainerType):
            result += 1
        elif isinstance(TYPE, lltype.GcStruct):
            result += _count_fields(TYPE)
        else:
            raise ValueError(TYPE)
    return result

# ____________________________________________________________

def has_gcstruct_a_vtable(GCSTRUCT):
    if not isinstance(GCSTRUCT, lltype.GcStruct):
        return False
    while not GCSTRUCT._hints.get('typeptr'):
        _, GCSTRUCT = GCSTRUCT._first_struct()
        if GCSTRUCT is None:
            return False
    return True

def get_vtable_for_gcstruct(cpu, GCSTRUCT):
    # xxx hack: from a GcStruct representing an instance's
    # lowleveltype, return the corresponding vtable pointer.
    # Returns None if the GcStruct does not belong to an instance.
    assert isinstance(GCSTRUCT, lltype.GcStruct)
    if not has_gcstruct_a_vtable(GCSTRUCT):
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

# ____________________________________________________________

VTABLETYPE = rclass.CLASSTYPE

def register_known_gctype(cpu, vtable, STRUCT):
    # register the correspondance 'vtable' <-> 'STRUCT' in the cpu
    sizedescr = cpu.sizeof(STRUCT)
    assert sizedescr.as_vtable_size_descr() is sizedescr
    try:
        assert sizedescr._corresponding_vtable == vtable
        return
    except AttributeError:
        pass
    assert lltype.typeOf(vtable) == VTABLETYPE
    if not hasattr(cpu, '_all_size_descrs_with_vtable'):
        cpu._all_size_descrs_with_vtable = []
        cpu._vtable_to_descr_dict = None
    cpu._all_size_descrs_with_vtable.append(sizedescr)
    sizedescr._corresponding_vtable = vtable

def finish_registering(cpu):
    # annotation hack for small examples which have no vtable at all
    if not hasattr(cpu, '_all_size_descrs_with_vtable'):
        vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        register_known_gctype(cpu, vtable, rclass.OBJECT)

def vtable2descr(cpu, vtable):
    assert lltype.typeOf(vtable) is lltype.Signed
    vtable = int2adr(vtable)
    if we_are_translated():
        # Build the dict {vtable: sizedescr} at runtime.
        # This is necessary because the 'vtables' are just pointers to
        # static data, so they can't be used as keys in prebuilt dicts.
        d = cpu._vtable_to_descr_dict
        if d is None:
            d = cpu._vtable_to_descr_dict = {}
            for descr in cpu._all_size_descrs_with_vtable:
                key = descr._corresponding_vtable
                key = llmemory.cast_ptr_to_adr(key)
                d[key] = descr
        return d[vtable]
    else:
        vtable = llmemory.cast_adr_to_ptr(vtable, VTABLETYPE)
        for descr in cpu._all_size_descrs_with_vtable:
            if descr._corresponding_vtable == vtable:
                return descr
        raise KeyError(vtable)

def descr2vtable(cpu, descr):
    from pypy.jit.metainterp import history
    assert isinstance(descr, history.AbstractDescr)
    vtable = descr.as_vtable_size_descr()._corresponding_vtable
    vtable = llmemory.cast_ptr_to_adr(vtable)
    return adr2int(vtable)
