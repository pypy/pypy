from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem import rclass
from pypy.objspace.flow.model import Constant


def rtype_new(hop):
    assert hop.args_s[0].is_constant()
    vlist = hop.inputargs(ootype.Void)
    return hop.genop('new', vlist,
                     resulttype = hop.r_result.lowleveltype)

def rtype_classof(hop):
    assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
    return hop.genop('classof', hop.args_v,
                     resulttype = ootype.Class)

def rtype_runtimenew(hop):
    assert isinstance(hop.args_s[0], annmodel.SomeOOClass)
    return hop.genop('runtimenew', hop.args_v,
                     resulttype = hop.r_result.lowleveltype)

def rtype_ooidentityhash(hop):
    assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
    return hop.genop('ooidentityhash', hop.args_v,
                     resulttype = ootype.Signed)

def rtype_builtin_isinstance(hop):
    if hop.s_result.is_constant():
        return hop.inputconst(ootype.Bool, hop.s_result.const)

    if hop.args_s[1].is_constant() and hop.args_s[1].const == list:
        if hop.args_s[0].knowntype != list:
            raise TyperError("isinstance(x, list) expects x to be known statically to be a list or None")
        raise TyperError("XXX missing impl of isinstance(x, list)")

    class_repr = rclass.get_type_repr(hop.rtyper)
    instance_repr = hop.args_r[0]
    assert isinstance(instance_repr, rclass.InstanceRepr)

    v_obj, v_cls = hop.inputargs(instance_repr, class_repr)
    if isinstance(v_cls, Constant):
        c_cls = hop.inputconst(ootype.Void, v_cls.value._INSTANCE)
        return hop.genop('instanceof', [v_obj, c_cls], resulttype=ootype.Bool)
    else:
        raise TyperError("XXX missing impl of isinstance(x, variable)")


BUILTIN_TYPER = {}
BUILTIN_TYPER[ootype.new] = rtype_new
BUILTIN_TYPER[ootype.classof] = rtype_classof
BUILTIN_TYPER[ootype.runtimenew] = rtype_runtimenew
BUILTIN_TYPER[ootype.ooidentityhash] = rtype_ooidentityhash
BUILTIN_TYPER[isinstance] = rtype_builtin_isinstance
