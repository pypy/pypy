from pypy.jit.metainterp.typesystem import deref, fieldType, arrayItem
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.backendopt.graphanalyze import BoolGraphAnalyzer


class EffectInfo(object):
    _cache = {}

    # the 'extraeffect' field is one of the following values:
    EF_PURE                            = 0 #pure function (and cannot raise)
    EF_CANNOT_RAISE                    = 1 #a function which cannot raise
    EF_CAN_RAISE                       = 2 #normal function (can raise)
    EF_LOOPINVARIANT                   = 3 #special: call it only once per loop
    EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE = 4 #can raise and force virtualizables

    # the 'oopspecindex' field is one of the following values:
    OS_NONE                     = 0    # normal case, no oopspec
    OS_ARRAYCOPY                = 1    # "list.ll_arraycopy"
    OS_STR2UNICODE              = 2    # "str.str2unicode"
    #
    OS_STR_CONCAT               = 22   # "stroruni.concat"
    OS_STR_SLICE                = 23   # "stroruni.slice"
    OS_STR_EQUAL                = 24   # "stroruni.equal"
    OS_STREQ_SLICE_CHECKNULL    = 25   # s2!=NULL and s1[x:x+length]==s2
    OS_STREQ_SLICE_NONNULL      = 26   # s1[x:x+length]==s2   (assert s2!=NULL)
    OS_STREQ_SLICE_CHAR         = 27   # s1[x:x+length]==char
    OS_STREQ_NONNULL            = 28   # s1 == s2    (assert s1!=NULL,s2!=NULL)
    OS_STREQ_NONNULL_CHAR       = 29   # s1 == char  (assert s1!=NULL)
    OS_STREQ_CHECKNULL_CHAR     = 30   # s1!=NULL and s1==char
    OS_STREQ_LENGTHOK           = 31   # s1 == s2    (assert len(s1)==len(s2))
    #
    OS_UNI_CONCAT               = 42   #
    OS_UNI_SLICE                = 43   #
    OS_UNI_EQUAL                = 44   #
    OS_UNIEQ_SLICE_CHECKNULL    = 45   #
    OS_UNIEQ_SLICE_NONNULL      = 46   #
    OS_UNIEQ_SLICE_CHAR         = 47   #
    OS_UNIEQ_NONNULL            = 48   #   the same for unicode
    OS_UNIEQ_NONNULL_CHAR       = 49   #   (must be the same amount as for
    OS_UNIEQ_CHECKNULL_CHAR     = 50   #   STR, in the same order)
    OS_UNIEQ_LENGTHOK           = 51   #
    _OS_offset_uni              = OS_UNI_CONCAT - OS_STR_CONCAT
    #
    OS_LIBFFI_PREPARE           = 60
    OS_LIBFFI_PUSH_ARG          = 61
    OS_LIBFFI_CALL              = 62

    def __new__(cls, readonly_descrs_fields,
                write_descrs_fields, write_descrs_arrays,
                extraeffect=EF_CAN_RAISE,
                oopspecindex=OS_NONE):
        key = (frozenset(readonly_descrs_fields),
               frozenset(write_descrs_fields),
               frozenset(write_descrs_arrays),
               extraeffect,
               oopspecindex)
        if key in cls._cache:
            return cls._cache[key]
        result = object.__new__(cls)
        result.readonly_descrs_fields = readonly_descrs_fields
        result.write_descrs_fields = write_descrs_fields
        result.write_descrs_arrays = write_descrs_arrays
        result.extraeffect = extraeffect
        result.oopspecindex = oopspecindex
        cls._cache[key] = result
        return result

    def check_forces_virtual_or_virtualizable(self):
        return self.extraeffect >= self.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE

def effectinfo_from_writeanalyze(effects, cpu,
                                 extraeffect=EffectInfo.EF_CAN_RAISE,
                                 oopspecindex=EffectInfo.OS_NONE):
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
                      extraeffect,
                      oopspecindex)

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

# ____________________________________________________________

_callinfo_for_oopspec = {} # {oopspecindex: (calldescr, func_as_int)}

def callinfo_for_oopspec(oopspecindex):
    """A function that returns the calldescr and the function
    address (as an int) of one of the OS_XYZ functions defined above.
    Don't use this if there might be several implementations of the same
    OS_XYZ specialized by type, e.g. OS_ARRAYCOPY."""
    try:
        return _callinfo_for_oopspec[oopspecindex]
    except KeyError:
        return (None, 0)


def _funcptr_for_oopspec_memo(oopspecindex):
    from pypy.jit.codewriter import heaptracker
    _, func_as_int = callinfo_for_oopspec(oopspecindex)
    funcadr = heaptracker.int2adr(func_as_int)
    return funcadr.ptr
_funcptr_for_oopspec_memo._annspecialcase_ = 'specialize:memo'

def funcptr_for_oopspec(oopspecindex):
    """A memo function that returns a pointer to the function described
    by OS_XYZ (as a real low-level function pointer)."""
    funcptr = _funcptr_for_oopspec_memo(oopspecindex)
    assert funcptr
    return funcptr
funcptr_for_oopspec._annspecialcase_ = 'specialize:arg(0)'
