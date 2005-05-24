from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, annotation_to_lltype
from pypy.annotation.model import SomePBC
from pypy.rpython.lltype import PyObject, GcPtr, Void
from pypy.rpython.rtyper import TyperError, peek_at_result_annotation
from pypy.rpython.rtyper import receiveconst


PyObjPtr = GcPtr(PyObject)


class __extend__(SomeObject):

    def lowleveltype(s_obj):
        try:
            return annotation_to_lltype(s_obj)
        except ValueError:
            if s_obj.is_constant():
                return Void
            else:
                return PyObjPtr


class __extend__(pairtype(SomeObject, SomeObject)):

    def rtype_convert_from_to((s_from, s_to), v):
        FROM = s_from.lowleveltype()
        TO   = s_to.lowleveltype()
        if PyObjPtr == FROM == TO:
            return v
        else:
            raise TyperError("don't know how to convert from %r to %r" % (
                s_from, s_to))


class __extend__(SomePBC):

    def rtype_getattr(s_pbc, s_attr):
        attr = s_attr.const
        s_result = peek_at_result_annotation()
        if s_result.is_constant():
            return receiveconst(s_result, s_result.const)
        else:
            NotImplementedYet
