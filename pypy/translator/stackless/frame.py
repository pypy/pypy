from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import extfunctable
from pypy.rpython.typesystem import getfunctionptr
from pypy.objspace.flow.model import FunctionGraph

# ____________________________________________________________
# generic data types

SAVED_REFERENCE = lltype.Ptr(lltype.GcOpaqueType('stackless.saved_ref'))
null_saved_ref = lltype.nullptr(SAVED_REFERENCE.TO)

STORAGE_TYPES = [lltype.Void, SAVED_REFERENCE, llmemory.Address,
                 lltype.Signed, lltype.Float, lltype.SignedLongLong]

STORAGE_FIELDS = {SAVED_REFERENCE: 'ref',
                  llmemory.Address: 'addr',
                  lltype.Signed: 'long',
                  lltype.Float: 'float',
                  lltype.SignedLongLong: 'longlong',
                  }

RETVAL_VOID = 0
for _key, _value in STORAGE_FIELDS.items():
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
                           ('f_restart', lltype.Signed))
STATE_HEADER.f_back.TO.become(STATE_HEADER)

null_state = lltype.nullptr(STATE_HEADER)

OPAQUE_STATE_HEADER_PTR = lltype.Ptr(
    extfunctable.frametop_type_info.get_lltype())


def make_state_header_type(name, *fields):
##    source = ['def ll_reccopy_%s(frame):' % name,
##              '    if frame.f_back:'
##              '        prev = frame.f_back.XXX',
##              '    newframe = lltype.malloc(lltype.typeOf(FRAME))',
##              '    newframe.']
    
##    copynames = [name for (name, _) in fields]
##    copynames.append('header.restartstate')
##    copynames.append('header.function')
##    copynames.append('header.retval_type')
##    for name in copynames:
##        source.append('    newframe.%s = frame.%s' % (name, name))
##    source.append('    return newframe')
##    source.append('')
##    miniglobals = {'lltype': lltype}
##    exec compile2('\n'.join(source)) in miniglobals
##    extras = {
##        'adtmeths': {'reccopy': miniglobals['ll_frame_reccopy']}
##        }
    return lltype.GcStruct(name,
                           ('header', STATE_HEADER),
                           *fields)

# ____________________________________________________________
# master array giving information about the restart points
# (STATE_HEADER.frameinfo is an index into this array)

FRAME_INFO = lltype.Struct('frame_info',
                           ('fnaddr', llmemory.Address),
                           ('info',   lltype.Signed))
FRAME_INFO_ARRAY = lltype.Array(FRAME_INFO)

def decodestate(masterarray, index):
    finfo = masterarray[index]
    if finfo.fnaddr:
        restartstate = 0
    else:
        restartstate = finfo.info
        finfo = masterarray[index - restartstate]
    return (finfo.fnaddr,  # function ptr
            restartstate,  # restart state within function
            finfo.info)    # retval_type
decodestate.stackless_explicit = True


class RestartInfo(object):
    __slots__ = ['func_or_graph',
                 'first_index',
                 'nb_restart_states']

    def __init__(self, func_or_graph, first_index, nb_restart_states):
        self.func_or_graph = func_or_graph
        self.first_index = first_index
        self.nb_restart_states = nb_restart_states

    def compress(self, rtyper, masterarray):
        if self.nb_restart_states > 0:
            graph = self.func_or_graph
            if not isinstance(graph, FunctionGraph):
                bk = rtyper.annotator.bookkeeper
                graph = bk.getdesc(graph).getuniquegraph()
            funcptr = getfunctionptr(graph)
            rettype = lltype.typeOf(funcptr).TO.RESULT
            retval_type = STORAGE_TYPES.index(storage_type(rettype))

            finfo = masterarray[self.first_index]
            finfo.fnaddr = llmemory.cast_ptr_to_adr(funcptr)
            finfo.info = retval_type
            for i in range(1, self.nb_restart_states):
                finfo = masterarray[self.first_index+i]
                finfo.info = i

    prebuilt = []
    prebuiltindex = 0

    def add_prebuilt(cls, func, nb_restart_states):
        assert func.stackless_explicit    # did you forget this flag?
        n = cls.prebuiltindex
        restart = cls(func, n, nb_restart_states)
        cls.prebuilt.append(restart)
        cls.prebuiltindex += restart.nb_restart_states
        return n
    add_prebuilt = classmethod(add_prebuilt)
