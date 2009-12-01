from pypy.jit.metainterp.typesystem import deref, fieldType, arrayItem
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.backendopt.graphanalyze import BoolGraphAnalyzer

class EffectInfo(object):
    _cache = {}

    def __new__(cls, write_descrs_fields, write_descrs_arrays,
                promotes_virtualizables=False):
        key = (frozenset(write_descrs_fields), frozenset(write_descrs_arrays),
               promotes_virtualizables)
        if key in cls._cache:
            return cls._cache[key]
        result = object.__new__(cls)
        result.write_descrs_fields = write_descrs_fields
        result.write_descrs_arrays = write_descrs_arrays
        result.promotes_virtualizables = promotes_virtualizables
        cls._cache[key] = result
        return result

def effectinfo_from_writeanalyze(effects, cpu, promotes_virtualizables=False):
    from pypy.translator.backendopt.writeanalyze import top_set
    if effects is top_set:
        return None
    write_descrs_fields = []
    write_descrs_arrays = []
    for tup in effects:
        if tup[0] == "struct":
            _, T, fieldname = tup
            T = deref(T)
            if not consider_struct(T, fieldname):
                continue
            descr = cpu.fielddescrof(T, fieldname)
            write_descrs_fields.append(descr)
        elif tup[0] == "array":
            _, T = tup
            ARRAY = deref(T)
            if not consider_array(ARRAY):
                continue
            descr = cpu.arraydescrof(ARRAY)
            write_descrs_arrays.append(descr)
        else:
            assert 0
    return EffectInfo(write_descrs_fields, write_descrs_arrays,
                      promotes_virtualizables)

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
        return op.opname == 'promote_virtualizable'
