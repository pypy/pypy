from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import PyObject, Ptr, Void, Bool, pyobjectptr
from pypy.rpython.rmodel import Repr, TyperError
from pypy.rpython import rclass


class __extend__(annmodel.SomeObject):
    def rtyper_makerepr(self, rtyper):
        if self.is_constant():
            return constpyobj_repr
        if self.knowntype is type:
            return rclass.get_type_repr(rtyper)
        else:
            return pyobj_repr
    def rtyper_makekey(self):
        if self.is_constant():
            return "const"
        if self.knowntype is type:
            return "type"
        else:
            return "pyobj"


class PyObjRepr(Repr):
    lowleveltype = Ptr(PyObject)

    def convert_const(self, value):
        return pyobjectptr(value)

pyobj_repr = PyObjRepr()


class ConstPyObjRepr(Repr):
    lowleveltype = Void

constpyobj_repr = ConstPyObjRepr()
