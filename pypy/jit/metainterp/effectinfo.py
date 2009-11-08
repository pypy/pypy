from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype

class EffectInfo(object):
    _cache = {}

    def __new__(cls, write_descrs_fields, write_descrs_arrays):
        key = frozenset(write_descrs_fields), frozenset(write_descrs_arrays)
        if key in cls._cache:
            return cls._cache[key]
        result = object.__new__(cls)
        result.write_descrs_fields = write_descrs_fields
        result.write_descrs_arrays = write_descrs_arrays
        cls._cache[key] = result
        return result

def effectinfo_from_writeanalyze(effects, cpu):
    from pypy.translator.backendopt.writeanalyze import top_set
    if effects is top_set:
        return None
    write_descrs_fields = []
    write_descrs_arrays = []
    for tup in effects:
        if tup[0] == "struct":
            _, T, fieldname = tup
            if not isinstance(T.TO, lltype.GcStruct): # can be a non-GC-struct
                continue
            if getattr(T.TO, fieldname) is lltype.Void:
                continue
            if fieldname == "typeptr" and T.TO is OBJECT:
                # filter out the typeptr, because
                # a) it is optimized in different ways
                # b) it might not be there in C if removetypeptr is specified
                continue
            descr = cpu.fielddescrof(T.TO, fieldname)
            write_descrs_fields.append(descr)
        elif tup[0] == "array":
            _, T = tup
            if not isinstance(T.TO, lltype.GcArray): # can be a non-GC-array
                continue
            if T.TO.OF is lltype.Void:
                continue
            descr = cpu.arraydescrof(T.TO)
            write_descrs_arrays.append(descr)
        else:
            assert 0
    return EffectInfo(write_descrs_fields, write_descrs_arrays)


