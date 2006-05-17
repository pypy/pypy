from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem import rclass
from pypy.objspace.flow.model import Constant


def rtype_new(hop):
    assert hop.args_s[0].is_constant()
    vlist = hop.inputargs(ootype.Void)
    return hop.genop('new', vlist,
                     resulttype = hop.r_result.lowleveltype)

def rtype_null(hop):
    assert hop.args_s[0].is_constant()
    TYPE = hop.args_s[0].const
    nullvalue = ootype.null(TYPE)
    return hop.inputconst(TYPE, nullvalue)

def rtype_classof(hop):
    assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
    return hop.genop('classof', hop.args_v,
                     resulttype = ootype.Class)

def rtype_subclassof(hop):
    assert isinstance(hop.args_s[0], annmodel.SomeOOClass)
    assert isinstance(hop.args_s[1], annmodel.SomeOOClass)
    return hop.genop('subclassof', hop.args_v,
                     resulttype = ootype.Bool)

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
        c_cls = hop.inputconst(ootype.Void, v_cls.value.class_._INSTANCE)
        return hop.genop('instanceof', [v_obj, c_cls], resulttype=ootype.Bool)
    else:
        raise TyperError("XXX missing impl of isinstance(x, variable)")

def rtype_oostring(hop):
    assert isinstance(hop.args_s[0],(annmodel.SomeInteger,
                                     annmodel.SomeChar,
                                     annmodel.SomeString,
                                     annmodel.SomeOOInstance))
    assert isinstance(hop.args_s[1], annmodel.SomeInteger)
    return hop.genop('oostring', hop.args_v, resulttype = ootype.String)

def rtype_ooparse_int(hop):
    assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)\
           and hop.args_s[0].ootype is ootype.String
    assert isinstance(hop.args_s[1], annmodel.SomeInteger)
    hop.has_implicit_exception(ValueError)
    hop.exception_is_here()
    return hop.genop('ooparse_int', hop.args_v, resulttype = ootype.Signed)

BUILTIN_TYPER = {}
BUILTIN_TYPER[ootype.new] = rtype_new
BUILTIN_TYPER[ootype.null] = rtype_null
BUILTIN_TYPER[ootype.classof] = rtype_classof
BUILTIN_TYPER[ootype.subclassof] = rtype_subclassof
BUILTIN_TYPER[ootype.runtimenew] = rtype_runtimenew
BUILTIN_TYPER[ootype.ooidentityhash] = rtype_ooidentityhash
BUILTIN_TYPER[isinstance] = rtype_builtin_isinstance
BUILTIN_TYPER[ootype.oostring] = rtype_oostring
BUILTIN_TYPER[ootype.ooparse_int] = rtype_ooparse_int
