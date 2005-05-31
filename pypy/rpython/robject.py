from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, annotation_to_lltype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import PyObject, GcPtr, Void
from pypy.rpython.rtyper import TyperError


PyObjPtr = GcPtr(PyObject)


def missing_rtype_operation(args, hop):
    raise TyperError("unimplemented operation: '%s' on %r" % (
        hop.spaceop.opname, args))

for opname in annmodel.UNARY_OPERATIONS:
    setattr(SomeObject, 'rtype_' + opname, missing_rtype_operation)
for opname in annmodel.BINARY_OPERATIONS:
    setattr(pairtype(SomeObject, SomeObject),
            'rtype_' + opname, missing_rtype_operation)


class __extend__(SomeObject):

    def lowleveltype(s_obj):
        try:
            return annotation_to_lltype(s_obj)
        except ValueError:
            if s_obj.is_constant():
                return Void
            else:
                return PyObjPtr

    def rtype_getattr(s_obj, hop):
        s_attr = hop.args_s[1]
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            try:
                s_obj.find_method(attr)   # just to check it is here
            except AttributeError:
                raise TyperError("no method %s on %r" % (attr, s_obj))
            else:
                # implement methods (of a known name) as just their 'self'
                return hop.inputarg(s_obj, arg=0)
        else:
            raise TyperError("getattr() with a non-constant attribute name")


class __extend__(pairtype(SomeObject, SomeObject)):

    def rtype_convert_from_to((s_from, s_to), v, llops):
        FROM = s_from.lowleveltype()
        TO   = s_to.lowleveltype()
        if PyObjPtr == FROM == TO:
            return v
        else:
            return NotImplemented
