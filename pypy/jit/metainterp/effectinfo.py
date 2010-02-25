from pypy.jit.metainterp.typesystem import deref, fieldType, arrayItem
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.backendopt.graphanalyze import BoolGraphAnalyzer

class EffectInfo(object):
    _cache = {}

    def __new__(cls, readonly_descrs_fields,
                write_descrs_fields, write_descrs_arrays,
                forces_virtual_or_virtualizable=False):
        key = (frozenset(readonly_descrs_fields),
               frozenset(write_descrs_fields),
               frozenset(write_descrs_arrays),
               forces_virtual_or_virtualizable)
        if key in cls._cache:
            return cls._cache[key]
        result = object.__new__(cls)
        result.readonly_descrs_fields = readonly_descrs_fields
        result.write_descrs_fields = write_descrs_fields
        result.write_descrs_arrays = write_descrs_arrays
        result.forces_virtual_or_virtualizable= forces_virtual_or_virtualizable
        cls._cache[key] = result
        return result

def effectinfo_from_writeanalyze(effects, cpu,
                                 forces_virtual_or_virtualizable=False):
    from pypy.translator.backendopt.writeanalyze import top_set
    if effects is top_set:
        return None
    readonly_descrs_fields = []
    # readonly_descrs_arrays = [] --- not enabled for now
    write_descrs_fields = []
    write_descrs_arrays = []

    def add_struct(descrs_fields, (_, T, fieldname)):
        T = deref(T)
        if consider_struct(T, fieldname):
            descr = cpu.fielddescrof(T, fieldname)
            descrs_fields.append(descr)

    def add_array(descrs_arrays, (_, T)):
        ARRAY = deref(T)
        if consider_array(ARRAY):
            descr = cpu.arraydescrof(ARRAY)
            descrs_arrays.append(descr)

    for tup in effects:
        if tup[0] == "struct":
            add_struct(write_descrs_fields, tup)
        elif tup[0] == "readstruct":
            tupw = ("struct",) + tup[1:]
            if tupw not in effects:
                add_struct(readonly_descrs_fields, tup)
        elif tup[0] == "array":
            add_array(write_descrs_arrays, tup)
        elif tup[0] == "readarray":
            pass
        else:
            assert 0
    return EffectInfo(readonly_descrs_fields,
                      write_descrs_fields,
                      write_descrs_arrays,
                      forces_virtual_or_virtualizable)

def consider_struct(TYPE, fieldname):
    if fieldType(TYPE, fieldname) is lltype.Void:
        return False
    if isinstance(TYPE, ootype.OOType):
        return True
    if not isinstance(TYPE, lltype.GcStruct): # can be a non-GC-struct
        return False
    if fieldname == "typeptr" and TYPE is OBJECT:
        # filter out the typeptr, because
        # a) it is optimized in different ways
        # b) it might not be there in C if removetypeptr is specified
        return False
    return True

def consider_array(ARRAY):
    if arrayItem(ARRAY) is lltype.Void:
        return False
    if isinstance(ARRAY, ootype.Array):
        return True
    if not isinstance(ARRAY, lltype.GcArray): # can be a non-GC-array
        return False
    return True

# ____________________________________________________________

class VirtualizableAnalyzer(BoolGraphAnalyzer):
    def analyze_simple_operation(self, op):
        return op.opname in ('jit_force_virtualizable',
                             'jit_force_virtual')
