from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import extfunctable
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.annlowlevel import annotate_lowlevel_helper
from pypy.objspace.flow.model import FunctionGraph
from pypy.tool.sourcetools import compile2
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator

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
    fnname = 'll_reccopy_%s' % (name,)
    source = ['def %s(frame):' % (fnname,),
              '    frame = lltype.cast_pointer(lltype.Ptr(FRAME), frame)',
              '    newframe = lltype.malloc(FRAME)',
              '    if frame.header.f_back:',
              '        newframe.header.f_back = ll_frame_reccopy(',
              '                                     frame.header.f_back)',
              '    newframe.header.f_restart = frame.header.f_restart']
    for name, _ in fields:
        source.append('    newframe.%s = frame.%s' % (name, name))
    source.append('    return lltype.cast_pointer(lltype.Ptr(STATE_HEADER),')
    source.append('                               newframe)')
    source.append('')
    miniglobals = {'lltype': lltype,
                   'll_frame_reccopy': ll_frame_reccopy,
                   'STATE_HEADER': STATE_HEADER,
                   }
    exec compile2('\n'.join(source)) in miniglobals
    extras = {
        'adtmeths': {'reccopy': miniglobals[fnname]}
        }
    FRAME = lltype.GcStruct(name,
                            ('header', STATE_HEADER),
                            *fields, **extras)
    miniglobals['FRAME'] = FRAME
    return FRAME

# ____________________________________________________________
# master array giving information about the restart points
# (STATE_HEADER.frameinfo is an index into this array)

RECCOPY_FUNC = lltype.FuncType([lltype.Ptr(STATE_HEADER)],
                               lltype.Ptr(STATE_HEADER))

FRAME_INFO = lltype.Struct('frame_info',
                           ('fnaddr',  llmemory.Address),
                           ('info',    lltype.Signed),
                           ('reccopy', lltype.Ptr(RECCOPY_FUNC)))
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
            finfo.info)    # retval_type
decodestate.stackless_explicit = True

def ll_frame_reccopy(frame):
    from pypy.translator.stackless.code import global_state
    masterarray = global_state.masterarray
    finfo = masterarray[frame.f_restart]
    return finfo.reccopy(frame)


class RestartInfo(object):

    def __init__(self, func_or_graph, frame_types):
        self.func_or_graph = func_or_graph
        self.frame_types = frame_types

    def compress(self, rtyper):
        if self.frame_types:
            bk = rtyper.annotator.bookkeeper
            graph = self.func_or_graph
            if not isinstance(graph, FunctionGraph):
                graph = bk.getdesc(graph).getuniquegraph()
            funcptr = getfunctionptr(graph)
            rettype = lltype.typeOf(funcptr).TO.RESULT
            retval_type = STORAGE_TYPES.index(storage_type(rettype))

            result = [{'fnaddr': llmemory.cast_ptr_to_adr(funcptr),
                       'info':   retval_type},
                      ]
            for i in range(1, len(self.frame_types)):
                result.append({'info': i})
            for i in range(len(self.frame_types)):
                reccopy = self.frame_types[i].reccopy
                s_header = annmodel.SomePtr(lltype.Ptr(STATE_HEADER))
                mixlevelannotator = MixLevelHelperAnnotator(rtyper)
                fnptr = mixlevelannotator.delayedfunction(reccopy, [s_header],
                                                          s_header)
                mixlevelannotator.finish()
                result[i]['reccopy'] = fnptr
        else:
            result = []
        return result

    prebuilt = []
    prebuiltindex = 0

    def add_prebuilt(cls, func, frame_types):
        assert func.stackless_explicit    # did you forget this flag?
        restart = cls(func, frame_types)
        n = cls.prebuiltindex
        cls.prebuilt.append(restart)
        cls.prebuiltindex += len(frame_types)
        return n
    add_prebuilt = classmethod(add_prebuilt)
