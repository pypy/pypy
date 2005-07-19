from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import PyObject, Ptr, Void, Bool, pyobjectptr, nullptr
from pypy.rpython.rmodel import Repr, TyperError, VoidRepr, inputconst
from pypy.rpython import rclass
from pypy.tool.sourcetools import func_with_new_name


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
            return self.__class__, "const"
        if self.knowntype is type:
            return self.__class__, "type"
        else:
            return self.__class__, "pyobj"


class PyObjRepr(Repr):
    def convert_const(self, value):
        return pyobjectptr(value)

pyobj_repr = PyObjRepr()
pyobj_repr.lowleveltype = Ptr(PyObject)
constpyobj_repr = PyObjRepr()
constpyobj_repr.lowleveltype = Void


class __extend__(pairtype(VoidRepr, PyObjRepr)):
    # conversion used to return a PyObject* when a function can really only
    # raise an exception, in which case the return value is a VoidRepr
    def convert_from_to(_, v, llops):
        return inputconst(Ptr(PyObject), nullptr(PyObject))


# ____________________________________________________________
#
#  All operations involving a PyObjRepr are "replaced" by themselves,
#  after converting all other arguments to PyObjRepr as well.  This
#  basically defers the operations to the care of the code generator.

def make_operation(opname, cls=PyObjRepr):
    def rtype_op(_, hop):
        vlist = hop.inputargs(*([pyobj_repr]*hop.nb_args))
        if isinstance(hop.r_result, VoidRepr):
            hop.genop(opname, vlist)
        else:
            v = hop.genop(opname, vlist, resulttype=pyobj_repr)
            return hop.llops.convertvar(v, pyobj_repr, hop.r_result)

    funcname = 'rtype_' + opname
    func = func_with_new_name(rtype_op, funcname)
    assert funcname not in cls.__dict__  # can be in Repr; overridden then.
    setattr(cls, funcname, func)


for opname in annmodel.UNARY_OPERATIONS:
    make_operation(opname)

for opname in annmodel.BINARY_OPERATIONS:
    make_operation(opname, pairtype(PyObjRepr, Repr))
    make_operation(opname, pairtype(Repr, PyObjRepr))
