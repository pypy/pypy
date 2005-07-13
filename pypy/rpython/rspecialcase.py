from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython import rclass
from pypy.rpython.rmodel import TyperError, inputconst


def rtype_call_specialcase(hop):
    v_function = hop.args_v[0]
    if not isinstance(v_function, Constant):
        raise TyperError("call_specialcase on a variable function")
    func = v_function.value
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
    return rtype_override_fn(hop2)


# def rtype_override_XXX to be added later


def rtype_override_ignore(hop):
    return inputconst(hop.r_result, None)
