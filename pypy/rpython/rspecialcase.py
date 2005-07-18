from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython import rclass
from pypy.rpython.rmodel import TyperError, inputconst


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
    return inputconst(hop.r_result, None)
