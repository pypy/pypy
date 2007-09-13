from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype, rootype
from pypy.rpython.ootypesystem import rclass
from pypy.rpython.ootypesystem.rdict import rtype_r_dict
from pypy.objspace.flow.model import Constant
from pypy.rlib import objectmodel
from pypy.rpython.error import TyperError

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
    vlist = hop.inputargs(hop.args_r[0])
    return hop.genop('classof', vlist,
                     resulttype = ootype.Class)

def rtype_subclassof(hop):
    vlist = hop.inputargs(rootype.ooclass_repr, rootype.ooclass_repr)
    return hop.genop('subclassof', vlist,
                     resulttype = ootype.Bool)

def rtype_runtimenew(hop):
    vlist = hop.inputargs(rootype.ooclass_repr)
    return hop.genop('runtimenew', vlist,
                     resulttype = hop.r_result.lowleveltype)

def rtype_ooidentityhash(hop):
    assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
    vlist = hop.inputargs(hop.args_r[0])
    return hop.genop('ooidentityhash', vlist,
                     resulttype = ootype.Signed)

def rtype_builtin_isinstance(hop):
    if hop.s_result.is_constant():
        return hop.inputconst(ootype.Bool, hop.s_result.const)

    if hop.args_s[1].is_constant() and hop.args_s[1].const == list:
        if hop.args_s[0].knowntype != list:
            raise TyperError("isinstance(x, list) expects x to be known statically to be a list or None")
        v_list = hop.inputarg(hop.args_r[0], arg=0)
        return hop.genop('oononnull', [v_list], resulttype=ootype.Bool)

    class_repr = rclass.get_type_repr(hop.rtyper)
    instance_repr = hop.args_r[0]
    assert isinstance(instance_repr, rclass.InstanceRepr)

    v_obj, v_cls = hop.inputargs(instance_repr, class_repr)
    if isinstance(v_cls, Constant):
        c_cls = hop.inputconst(ootype.Void, v_cls.value.class_._INSTANCE)
        return hop.genop('instanceof', [v_obj, c_cls], resulttype=ootype.Bool)
    else:
        return hop.gendirectcall(ll_isinstance, v_obj, v_cls)

def ll_isinstance(inst, meta):
    c1 = inst.meta.class_
    c2 = meta.class_
    return ootype.subclassof(c1, c2)

def rtype_instantiate(hop):
    if hop.args_s[0].is_constant():
##        INSTANCE = hop.s_result.rtyper_makerepr(hop.rtyper).lowleveltype
##        v_instance = hop.inputconst(ootype.Void, INSTANCE)
##        hop2 = hop.copy()
##        hop2.r_s_popfirstarg()
##        s_instance = hop.rtyper.annotator.bookkeeper.immutablevalue(INSTANCE)
##        hop2.v_s_insertfirstarg(v_instance, s_instance)
##        return rtype_new(hop2)
        r_instance = hop.s_result.rtyper_makerepr(hop.rtyper)
        return r_instance.new_instance(hop.llops)
    else:
        r_instance = hop.s_result.rtyper_makerepr(hop.rtyper)
        INSTANCE = r_instance.lowleveltype
        c_instance = hop.inputconst(ootype.Void, INSTANCE)
        v_cls = hop.inputarg(hop.args_r[0], arg=0)
        v_obj = hop.gendirectcall(ll_instantiate, c_instance, v_cls)
        v_instance = hop.genop('oodowncast', [v_obj], resulttype=hop.r_result.lowleveltype)
        c_meta = hop.inputconst(ootype.Void, "meta")
        hop.genop("oosetfield", [v_instance, c_meta, v_cls], resulttype=ootype.Void)
        return v_instance

def ll_instantiate(INST, C):
    return ootype.runtimenew(C.class_)

BUILTIN_TYPER = {}
BUILTIN_TYPER[ootype.new] = rtype_new
BUILTIN_TYPER[ootype.null] = rtype_null
BUILTIN_TYPER[ootype.classof] = rtype_classof
BUILTIN_TYPER[ootype.subclassof] = rtype_subclassof
BUILTIN_TYPER[ootype.runtimenew] = rtype_runtimenew
BUILTIN_TYPER[ootype.ooidentityhash] = rtype_ooidentityhash
BUILTIN_TYPER[isinstance] = rtype_builtin_isinstance
BUILTIN_TYPER[objectmodel.r_dict] = rtype_r_dict
BUILTIN_TYPER[objectmodel.instantiate] = rtype_instantiate


# _________________________________________________________________
# weakrefs

import weakref
from pypy.rpython.lltypesystem import llmemory

def rtype_weakref_create(hop):
    # Note: this code also works for the RPython-level calls 'weakref.ref(x)'.
    vlist = hop.inputargs(hop.args_r[0])
    hop.exception_cannot_occur()
    return hop.gendirectcall(ootype.ooweakref_create, *vlist)

BUILTIN_TYPER[weakref.ref] = rtype_weakref_create
