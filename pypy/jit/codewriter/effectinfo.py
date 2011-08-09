from pypy.jit.metainterp.typesystem import deref, fieldType, arrayItem
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.backendopt.graphanalyze import BoolGraphAnalyzer


class EffectInfo(object):
    _cache = {}

    # the 'extraeffect' field is one of the following values:
    EF_ELIDABLE_CANNOT_RAISE           = 0 #elidable function (and cannot raise)
    EF_LOOPINVARIANT                   = 1 #special: call it only once per loop
    EF_CANNOT_RAISE                    = 2 #a function which cannot raise
    EF_ELIDABLE_CAN_RAISE              = 3 #elidable function (but can raise)
    EF_CAN_RAISE                       = 4 #normal function (can raise)
    EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE = 5 #can raise and force virtualizables
    EF_RANDOM_EFFECTS                  = 6 #can do whatever

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
    #
    OS_LLONG_INVERT             = 69
    OS_LLONG_ADD                = 70
    OS_LLONG_SUB                = 71
    OS_LLONG_MUL                = 72
    OS_LLONG_LT                 = 73
    OS_LLONG_LE                 = 74
    OS_LLONG_EQ                 = 75
    OS_LLONG_NE                 = 76
    OS_LLONG_GT                 = 77
    OS_LLONG_GE                 = 78
    OS_LLONG_AND                = 79
    OS_LLONG_OR                 = 80
    OS_LLONG_LSHIFT             = 81
    OS_LLONG_RSHIFT             = 82
    OS_LLONG_XOR                = 83
    OS_LLONG_FROM_INT           = 84
    OS_LLONG_TO_INT             = 85
    OS_LLONG_FROM_FLOAT         = 86
    OS_LLONG_TO_FLOAT           = 87
    OS_LLONG_ULT                = 88
    OS_LLONG_ULE                = 89
    OS_LLONG_UGT                = 90
    OS_LLONG_UGE                = 91
    OS_LLONG_URSHIFT            = 92
    OS_LLONG_FROM_UINT          = 93
    #
    OS_MATH_SQRT                = 100

    def __new__(cls, readonly_descrs_fields, readonly_descrs_arrays,
                write_descrs_fields, write_descrs_arrays,
                extraeffect=EF_CAN_RAISE,
                oopspecindex=OS_NONE,
                can_invalidate=False):
        key = (frozenset_or_none(readonly_descrs_fields),
               frozenset_or_none(readonly_descrs_arrays),
               frozenset_or_none(write_descrs_fields),
               frozenset_or_none(write_descrs_arrays),
               extraeffect,
               oopspecindex,
               can_invalidate)
        if key in cls._cache:
            return cls._cache[key]
        if extraeffect == EffectInfo.EF_RANDOM_EFFECTS:
            assert readonly_descrs_fields is None
            assert readonly_descrs_arrays is None
            assert write_descrs_fields is None
            assert write_descrs_arrays is None
        else:
            assert readonly_descrs_fields is not None
            assert readonly_descrs_arrays is not None
            assert write_descrs_fields is not None
            assert write_descrs_arrays is not None
        result = object.__new__(cls)
        result.readonly_descrs_fields = readonly_descrs_fields
        result.readonly_descrs_arrays = readonly_descrs_arrays
        if extraeffect == EffectInfo.EF_LOOPINVARIANT or \
           extraeffect == EffectInfo.EF_ELIDABLE_CANNOT_RAISE or \
           extraeffect == EffectInfo.EF_ELIDABLE_CAN_RAISE:
            result.write_descrs_fields = []
            result.write_descrs_arrays = []
        else:
            result.write_descrs_fields = write_descrs_fields
            result.write_descrs_arrays = write_descrs_arrays
        result.extraeffect = extraeffect
        result.can_invalidate = can_invalidate
        result.oopspecindex = oopspecindex
        cls._cache[key] = result
        return result

    def check_can_raise(self):
        return self.extraeffect > self.EF_CANNOT_RAISE

    def check_can_invalidate(self):
        return self.can_invalidate

    def check_forces_virtual_or_virtualizable(self):
        return self.extraeffect >= self.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE

    def has_random_effects(self):
        return self.extraeffect >= self.EF_RANDOM_EFFECTS


def frozenset_or_none(x):
    if x is None:
        return None
    return frozenset(x)

EffectInfo.MOST_GENERAL = EffectInfo(None, None, None, None,
                                     EffectInfo.EF_RANDOM_EFFECTS,
                                     can_invalidate=True)


def effectinfo_from_writeanalyze(effects, cpu,
                                 extraeffect=EffectInfo.EF_CAN_RAISE,
                                 oopspecindex=EffectInfo.OS_NONE,
                                 can_invalidate=False):
    from pypy.translator.backendopt.writeanalyze import top_set
    if effects is top_set or extraeffect == EffectInfo.EF_RANDOM_EFFECTS:
        readonly_descrs_fields = None
        readonly_descrs_arrays = None
        write_descrs_fields = None
        write_descrs_arrays = None
        extraeffect = EffectInfo.EF_RANDOM_EFFECTS
    else:
        readonly_descrs_fields = []
        readonly_descrs_arrays = []
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
                tupw = ("array",) + tup[1:]
                if tupw not in effects:
                    add_array(readonly_descrs_arrays, tup)
            else:
                assert 0
    #
    return EffectInfo(readonly_descrs_fields,
                      readonly_descrs_arrays,
                      write_descrs_fields,
                      write_descrs_arrays,
                      extraeffect,
                      oopspecindex,
                      can_invalidate)

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
    def analyze_simple_operation(self, op, graphinfo):
        return op.opname in ('jit_force_virtualizable',
                             'jit_force_virtual')

class QuasiImmutAnalyzer(BoolGraphAnalyzer):
    def analyze_simple_operation(self, op, graphinfo):
        return op.opname == 'jit_force_quasi_immutable'

class RandomEffectsAnalyzer(BoolGraphAnalyzer):
    def analyze_direct_call(self, graph, seen=None):
        if hasattr(graph, "func") and hasattr(graph.func, "_ptr"):
            if graph.func._ptr._obj.random_effects_on_gcobjs:
                return True
        return super(RandomEffectsAnalyzer, self).analyze_direct_call(graph,
                                                                      seen)

    def analyze_simple_operation(self, op, graphinfo):
        return False

# ____________________________________________________________

class CallInfoCollection(object):
    def __init__(self):
        # {oopspecindex: (calldescr, func_as_int)}
        self._callinfo_for_oopspec = {}

    def _freeze_(self):
        return True

    def add(self, oopspecindex, calldescr, func_as_int):
        self._callinfo_for_oopspec[oopspecindex] = calldescr, func_as_int

    def has_oopspec(self, oopspecindex):
        return oopspecindex in self._callinfo_for_oopspec

    def all_function_addresses_as_int(self):
        return [func for (_, func) in self._callinfo_for_oopspec.values()]

    def callinfo_for_oopspec(self, oopspecindex):
        """A function that returns the calldescr and the function
        address (as an int) of one of the OS_XYZ functions defined above.
        Don't use this if there might be several implementations of the same
        OS_XYZ specialized by type, e.g. OS_ARRAYCOPY."""
        try:
            return self._callinfo_for_oopspec[oopspecindex]
        except KeyError:
            return (None, 0)

    def _funcptr_for_oopspec_memo(self, oopspecindex):
        from pypy.jit.codewriter import heaptracker
        _, func_as_int = self.callinfo_for_oopspec(oopspecindex)
        funcadr = heaptracker.int2adr(func_as_int)
        return funcadr.ptr
    _funcptr_for_oopspec_memo._annspecialcase_ = 'specialize:memo'

    def funcptr_for_oopspec(self, oopspecindex):
        """A memo function that returns a pointer to the function described
        by OS_XYZ (as a real low-level function pointer)."""
        funcptr = self._funcptr_for_oopspec_memo(oopspecindex)
        assert funcptr
        return funcptr
    funcptr_for_oopspec._annspecialcase_ = 'specialize:arg(1)'
