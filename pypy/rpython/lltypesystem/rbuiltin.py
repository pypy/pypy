from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rclass
from pypy.rpython.lltypesystem.rdict import rtype_r_dict
from pypy.rpython import objectmodel
from pypy.rpython.rmodel import TyperError, Constant
from pypy.rpython.robject import pyobj_repr
from pypy.rpython.rbool import bool_repr

def rtype_builtin_isinstance(hop):
    if hop.s_result.is_constant():
        return hop.inputconst(lltype.Bool, hop.s_result.const)
    if hop.args_r[0] == pyobj_repr or hop.args_r[1] == pyobj_repr:
        v_obj, v_typ = hop.inputargs(pyobj_repr, pyobj_repr)
        c = hop.inputconst(pyobj_repr, isinstance)
        v = hop.genop('simple_call', [c, v_obj, v_typ], resulttype = pyobj_repr)
        return hop.llops.convertvar(v, pyobj_repr, bool_repr)        

    if hop.args_s[1].is_constant() and hop.args_s[1].const == list:
        if hop.args_s[0].knowntype != list:
            raise TyperError("isinstance(x, list) expects x to be known statically to be a list or None")
        rlist = hop.args_r[0]
        vlist = hop.inputarg(rlist, arg=0)
        cnone = hop.inputconst(rlist, None)
        return hop.genop('ptr_ne', [vlist, cnone], resulttype=lltype.Bool)

    assert isinstance(hop.args_r[0], rclass.InstanceRepr)
    return hop.args_r[0].rtype_isinstance(hop)

def ll_instantiate(typeptr):   # NB. used by rpbc.ClassesPBCRepr as well
    my_instantiate = typeptr.instantiate
    return my_instantiate()

def rtype_instantiate(hop):
    s_class = hop.args_s[0]
    assert isinstance(s_class, annmodel.SomePBC)
    if len(s_class.descriptions) != 1:
        # instantiate() on a variable class
        vtypeptr, = hop.inputargs(rclass.get_type_repr(hop.rtyper))
        v_inst = hop.gendirectcall(ll_instantiate, vtypeptr)
        return hop.genop('cast_pointer', [v_inst],    # v_type implicit in r_result
                         resulttype = hop.r_result.lowleveltype)

    classdef = s_class.descriptions.keys()[0].getuniqueclassdef()
    return rclass.rtype_new_instance(hop.rtyper, classdef, hop.llops)

def rtype_builtin_hasattr(hop):
    if hop.s_result.is_constant():
        return hop.inputconst(lltype.Bool, hop.s_result.const)
    if hop.args_r[0] == pyobj_repr:
        v_obj, v_name = hop.inputargs(pyobj_repr, pyobj_repr)
        c = hop.inputconst(pyobj_repr, hasattr)
        v = hop.genop('simple_call', [c, v_obj, v_name], resulttype = pyobj_repr)
        return hop.llops.convertvar(v, pyobj_repr, bool_repr)
    raise TyperError("hasattr is only suported on a constant or on PyObject")

def rtype_builtin___import__(hop):
    args_v = hop.inputargs(*[pyobj_repr for ign in hop.args_r])
    c = hop.inputconst(pyobj_repr, __import__)
    return hop.genop('simple_call', [c] + args_v, resulttype = pyobj_repr)

BUILTIN_TYPER = {}
BUILTIN_TYPER[objectmodel.instantiate] = rtype_instantiate
BUILTIN_TYPER[isinstance] = rtype_builtin_isinstance
BUILTIN_TYPER[hasattr] = rtype_builtin_hasattr
BUILTIN_TYPER[__import__] = rtype_builtin___import__
BUILTIN_TYPER[objectmodel.r_dict] = rtype_r_dict
