from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import inputconst


def rtype_call_specialcase(hop):
    s_function = hop.args_s[0]
    if len(s_function.prebuiltinstances) != 1:
        raise TyperError("not monomorphic call_specialcase")
    func, clsdef = s_function.prebuiltinstances.items()[0]
    tag = func._annspecialcase_
    if not tag.startswith("override:"):
        raise TyperError("call_specialcase only supports 'override:' functions")
    tag = tag[9:]
    try:
        rtype_override_fn = globals()['rtype_override_' + tag]
    except KeyError:
        raise TyperError("call_specialcase: unknown tag override:" + tag)
    hop2 = hop.copy()
    hop2.r_s_popfirstarg()
    return rtype_override_fn(hop2, clsdef)



def rtype_override_ignore(hop, clsdef): # ignore works for methods too
    hop.exception_cannot_occur()
    return inputconst(hop.r_result, None)

def rtype_identity_function(hop, clsdef):
    hop.exception_cannot_occur()
    v, = hop.inputargs(hop.args_r[0])
    return v

def rtype_override_init_opaque_object(hop, clsdef):
    return hop.genop('init_opaque_object_should_never_be_seen_by_the_backend',
                     [], resulttype=hop.r_result)

def rtype_override_from_opaque_object(hop, clsdef):
    return hop.genop('from_opaque_object_should_never_be_seen_by_the_backend',
                     [], resulttype=hop.r_result)

def rtype_override_to_opaque_object(hop, clsdef):
    return hop.genop('to_opaque_object_should_never_be_seen_by_the_backend',
                     [], resulttype=hop.r_result)

def rtype_override_yield_current_frame_to_caller(hop, clsdef):
    return hop.genop('yield_current_frame_to_caller', [], 
                     resulttype=hop.r_result)
