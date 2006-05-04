from pypy.objspace.flow.model import Constant
from pypy.rpython.rclass import getclassrepr, get_type_repr
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rclass import InstanceRepr, CLASSTYPE
from pypy.rpython.lltypesystem.rclass import MissingRTypeAttribute
from pypy.rpython.lltypesystem.rclass import ll_issubclass_const
from pypy.rpython.rmodel import TyperError, inputconst


class TaggedInstanceRepr(InstanceRepr):

    def __init__(self, rtyper, classdef, unboxedclassdef):
        InstanceRepr.__init__(self, rtyper, classdef)
        self.unboxedclassdef = unboxedclassdef
        self.is_parent = unboxedclassdef is not classdef

    def _setup_repr(self):
        InstanceRepr._setup_repr(self)
        if len(self.allinstancefields) != 1:
            raise TyperError("%r cannot have fields besides __class__: %r" % (
                self.classdef, self.allinstancefields.keys()))

    def new_instance(self, llops, classcallhop=None):
        if self.is_parent:
            raise TyperError("don't instantiate %r, it is a parent of an "
                             "UnboxedValue class" % (self.classdef,))
        if classcallhop is None:
            raise TyperError("must instantiate %r by calling the class" % (
                self.classdef,))
        hop = classcallhop
        if not (hop.spaceop.opname == 'simple_call' and hop.nb_args == 2):
            raise TyperError("must instantiate %r with a simple class call" % (
                self.classdef,))
        v_value = hop.inputarg(lltype.Signed, arg=1)
        c_one = hop.inputconst(lltype.Signed, 1)
        hop.exception_is_here()
        v2 = hop.genop('int_lshift_ovf', [v_value, c_one],
                       resulttype = lltype.Signed)
        v2p1 = hop.genop('int_add', [v2, c_one],
                         resulttype = lltype.Signed)
        v_instance =  hop.genop('cast_int_to_ptr', [v2p1],
                                resulttype = self.lowleveltype)
        return v_instance, False   # don't call __init__

    def convert_const(self, value):
        raise NotImplementedError

    def getfield(self, vinst, attr, llops, force_cast=False):
        if attr != '__class__':
            raise MissingRTypeAttribute(attr)
        unboxedclass_repr = getclassrepr(self.rtyper, self.unboxedclassdef)
        cunboxedcls = inputconst(CLASSTYPE, unboxedclass_repr.getvtable())
        if self.is_parent:
            vinst = llops.genop('cast_pointer', [vinst],
                                resulttype=self.common_repr())
            return llops.gendirectcall(ll_unboxed_getclass, vinst, cunboxedcls)
        else:
            return cunboxedcls

    def rtype_type(self, hop):
        raise NotImplementedError

    def rtype_setattr(self, hop):
        raise NotImplementedError

    def ll_str(self, i):
        raise NotImplementedError

    def rtype_isinstance(self, hop):
        if not hop.args_s[1].is_constant():
            raise TyperError("isinstance() too complicated")
        [classdesc] = hop.args_s[1].descriptions
        classdef = classdesc.getuniqueclassdef()

        class_repr = get_type_repr(self.rtyper)
        instance_repr = self.common_repr()
        v_obj, v_cls = hop.inputargs(instance_repr, class_repr)
        cls = v_cls.value
        answer = self.unboxedclassdef.issubclass(classdef)
        c_answer_if_unboxed = hop.inputconst(lltype.Bool, answer)
        minid = hop.inputconst(lltype.Signed, cls.subclassrange_min)
        maxid = hop.inputconst(lltype.Signed, cls.subclassrange_max)
        return hop.gendirectcall(ll_unboxed_isinstance_const, v_obj,
                                 minid, maxid, c_answer_if_unboxed)


def ll_unboxed_getclass(instance, class_if_unboxed):
    if lltype.cast_ptr_to_int(instance) & 1:
        return class_if_unboxed
    else:
        return instance.typeptr

def ll_unboxed_isinstance_const(obj, minid, maxid, answer_if_unboxed):
    if not obj:
        return False
    if lltype.cast_ptr_to_int(obj) & 1:
        return answer_if_unboxed
    else:
        return ll_issubclass_const(obj.typeptr, minid, maxid)

def rtype_getvalue_from_unboxed(hop):
    assert isinstance(hop.args_r[0], TaggedInstanceRepr)
    assert not hop.args_r[0].is_parent
    [v_instance] = hop.inputargs(hop.args_r[0])
    v2 = hop.genop('cast_ptr_to_int', [v_instance], resulttype = lltype.Signed)
    c_one = hop.inputconst(lltype.Signed, 1)
    return hop.genop('int_rshift',    [v2, c_one],  resulttype = lltype.Signed)

