from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import inputconst


def rtype_call_specialcase(hop):
    s_pbc = hop.args_s[0]
    if len(s_pbc.descriptions) != 1:
        raise TyperError("not monomorphic call_specialcase")
    desc, = s_pbc.descriptions
    tag = desc.pyobj._annspecialcase_
    if not tag.startswith("override:"):
        raise TyperError("call_specialcase only supports 'override:' functions")
    tag = tag[9:]
    try:
        rtype_override_fn = globals()['rtype_override_' + tag]
    except KeyError:
        raise TyperError("call_specialcase: unknown tag override:" + tag)
    hop2 = hop.copy()
    hop2.r_s_popfirstarg()
    return rtype_override_fn(hop2)



def rtype_override_ignore(hop): # ignore works for methods too
    hop.exception_cannot_occur()
    return inputconst(hop.r_result, None)

def rtype_identity_function(hop):
    hop.exception_cannot_occur()
    v, = hop.inputargs(hop.args_r[0])
    return v

def rtype_override_yield_current_frame_to_caller(hop):
    return hop.genop('yield_current_frame_to_caller', [], 
                     resulttype=hop.r_result)
