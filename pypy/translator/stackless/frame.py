from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.annlowlevel import annotate_lowlevel_helper
from pypy.objspace.flow.model import FunctionGraph
from pypy.tool.sourcetools import compile2
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.rlib import rstack

# ____________________________________________________________
# generic data types

SAVED_REFERENCE = llmemory.GCREF
null_saved_ref = lltype.nullptr(SAVED_REFERENCE.TO)

STORAGE_TYPES_AND_FIELDS = [
    (lltype.Void, 'void'),
    (SAVED_REFERENCE, 'ref'),
    (llmemory.Address, 'addr'),
    (lltype.SignedLongLong, 'longlong'),
    (lltype.Signed, 'long'),
    (lltype.Float, 'float'),
     ]

STORAGE_TYPES = []
for _TYPE, _FIELD in STORAGE_TYPES_AND_FIELDS:
    # we do not want to add the longlong type twice on 64 bits
    # machines on which longlong is the same as signed
    if _TYPE not in STORAGE_TYPES:
        STORAGE_TYPES.append(_TYPE)

storage_type_bitmask = 0x07     # a power of two - 1
assert storage_type_bitmask >= len(STORAGE_TYPES)

STORAGE_FIELDS = dict(STORAGE_TYPES_AND_FIELDS)
del STORAGE_FIELDS[lltype.Void]

for (_key, _value) in STORAGE_TYPES_AND_FIELDS:
    globals()['RETVAL_' + _value.upper()] = STORAGE_TYPES.index(_key)

def storage_type(T):
    """Return the 'erased' storage type corresponding to T.
    """
    if T is lltype.Void:
        return lltype.Void
    elif isinstance(T, lltype.Ptr):
        if T._needsgc():
            return SAVED_REFERENCE
        else:
            return llmemory.Address
    elif T is lltype.Float:
        return lltype.Float
    elif T in [lltype.SignedLongLong, lltype.UnsignedLongLong]:
        return lltype.SignedLongLong
    elif T is llmemory.Address:
        return llmemory.Address
    elif isinstance(T, lltype.Primitive):
        return lltype.Signed
    else:
        raise Exception("don't know about %r" % (T,))

# ____________________________________________________________
# structures for saved frame states

STATE_HEADER = lltype.GcStruct('state_header',
                           ('f_back', lltype.Ptr(lltype.GcForwardReference())),
                           ('f_restart', lltype.Signed),
                           ('f_depth', lltype.Signed))
STATE_HEADER.f_back.TO.become(STATE_HEADER)

null_state = lltype.nullptr(STATE_HEADER)

OPAQUE_STATE_HEADER_PTR = rstack.OPAQUE_STATE_HEADER_PTR


def make_state_header_type(name, *fields):
    return lltype.GcStruct(name,
                           ('header', STATE_HEADER),
                           *fields)

# ____________________________________________________________
# master array giving information about the restart points
# (STATE_HEADER.frameinfo is an index into this array)

FRAME_INFO = lltype.Struct('frame_info',
                           ('fnaddr',  llmemory.Address),
                           ('info',    lltype.Signed))
FRAME_INFO_ARRAY = lltype.Array(FRAME_INFO)

def decodestate(index):
    from pypy.translator.stackless.code import global_state
    masterarray = global_state.masterarray
    finfo = masterarray[index]
    if finfo.fnaddr:
        restartstate = 0
    else:
        restartstate = finfo.info
        finfo = masterarray[index - restartstate]
    return (finfo.fnaddr,  # function ptr
            restartstate,  # restart state within function
            finfo.info)    # signature_index
decodestate.stackless_explicit = True


class RestartInfo(object):

    """A RestartInfo is created (briefly) for each graph that contains
    a resume point.

    In addition, a RestartInfo is created for each function that needs
    to do explicit stackless manipulations
    (e.g. code.yield_current_frame_to_caller)."""

    def __init__(self, func_or_graph, resume_point_count):
        self.func_or_graph = func_or_graph
        self.resume_point_count = resume_point_count
        self.frame_types = ()

    def compress(self, signaturecodes, rtyper):
        """This returns sufficient information to be able to build the
        entries that will go in the global array of restart
        information."""
        if self.resume_point_count > 0:
            bk = rtyper.annotator.bookkeeper
            graph = self.func_or_graph
            if not isinstance(graph, FunctionGraph):
                graph = bk.getdesc(graph).getuniquegraph()
            funcptr = getfunctionptr(graph)
            FUNC = lltype.typeOf(funcptr).TO
            rettype_index = STORAGE_TYPES.index(storage_type(FUNC.RESULT))
            cache = signaturecodes[rettype_index]
            key = tuple([storage_type(ARG) for ARG in FUNC.ARGS])
            try:
                signature_index = cache[key]
            except KeyError:
                signature_index = len(cache) * (storage_type_bitmask+1)
                signature_index |= rettype_index
                cache[key] = signature_index
            assert (signature_index & storage_type_bitmask) == rettype_index
            result = [(llmemory.cast_ptr_to_adr(funcptr), signature_index)]
            for i in range(1, self.resume_point_count):
                result.append((llmemory.NULL, i))
        else:
            result = []
        return result

    prebuilt = []
    prebuiltindex = 0

    def add_prebuilt(cls, func, frame_types):
        assert func.stackless_explicit    # did you forget this flag?
        restart = cls(func, len(frame_types))
        restart.frame_types = frame_types
        n = cls.prebuiltindex
        cls.prebuilt.append(restart)
        cls.prebuiltindex += len(frame_types)
        return n
    add_prebuilt = classmethod(add_prebuilt)
