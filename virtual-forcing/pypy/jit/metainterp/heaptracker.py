from pypy.rpython.lltypesystem import lltype, rclass


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
