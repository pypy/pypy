from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, annotation_to_lltype
from pypy.rpython.lltype import PyObject, GcPtr, Void
from pypy.rpython.rtyper import TyperError
from pypy.rpython.rtyper import receiveconst, receive


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

    def rtype_getattr(s_obj, s_attr):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            try:
                s_obj.find_method(attr)   # just to check it is here
            except AttributeError:
                raise TyperError("no method %s on %r" % (attr, s_obj))
            else:
                # implement methods (of a known name) as just their 'self'
                return receive(s_obj, arg=0)
        else:
            raise TyperError("getattr() with a non-constant attribute name")


class __extend__(pairtype(SomeObject, SomeObject)):

    def rtype_convert_from_to((s_from, s_to), v):
        FROM = s_from.lowleveltype()
        TO   = s_to.lowleveltype()
        if PyObjPtr == FROM == TO:
            return v
        else:
            raise TyperError("don't know how to convert from %r to %r" % (
                s_from, s_to))
