from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rclass
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

    class_repr = rclass.get_type_repr(hop.rtyper)
    assert isinstance(hop.args_r[0], rclass.InstanceRepr)
    instance_repr = hop.args_r[0].common_repr()

    v_obj, v_cls = hop.inputargs(instance_repr, class_repr)
    if isinstance(v_cls, Constant):
        minid = hop.inputconst(lltype.Signed, v_cls.value.subclassrange_min)
        maxid = hop.inputconst(lltype.Signed, v_cls.value.subclassrange_max)
        return hop.gendirectcall(rclass.ll_isinstance_const, v_obj, minid,
                                 maxid)
    else:
        return hop.gendirectcall(rclass.ll_isinstance, v_obj, v_cls)

def ll_instantiate(typeptr):
    my_instantiate = typeptr.instantiate
    return my_instantiate()

def rtype_instantiate(hop):
    s_class = hop.args_s[0]
    assert isinstance(s_class, annmodel.SomePBC)
    if len(s_class.prebuiltinstances) != 1:
        # instantiate() on a variable class
        vtypeptr, = hop.inputargs(rclass.get_type_repr(hop.rtyper))
        v_inst = hop.gendirectcall(ll_instantiate, vtypeptr)
        return hop.genop('cast_pointer', [v_inst],    # v_type implicit in r_result
                         resulttype = hop.r_result.lowleveltype)


    klass = s_class.const
    return rclass.rtype_new_instance(hop.rtyper, klass, hop.llops)

BUILTIN_TYPER = {}
BUILTIN_TYPER[objectmodel.instantiate] = rtype_instantiate
BUILTIN_TYPER[isinstance] = rtype_builtin_isinstance
