from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.lltype import \
     PyObject, Ptr, Void, pyobjectptr, nullptr, Bool
from pypy.rpython.rmodel import Repr, VoidRepr, inputconst
from pypy.rpython import rclass
from pypy.tool.sourcetools import func_with_new_name


class __extend__(annmodel.SomeObject):
    def rtyper_makerepr(self, rtyper):
        kind = getkind(self)
        if kind == "type":
            return rclass.get_type_repr(rtyper)
        elif kind == "const":
            return constpyobj_repr
        else:
            return pyobj_repr
    def rtyper_makekey(self):
        return self.__class__, getkind(self)

def getkind(s_obj):
    if s_obj.is_constant():
        if getattr(s_obj.const, '__module__', None) == '__builtin__':
            return "const"
    if s_obj.knowntype is type:
        return "type"
    if s_obj.is_constant():
        return "const"
    return "pyobj"


class PyObjRepr(Repr):
    def convert_const(self, value):
        return pyobjectptr(value)
    def make_iterator_repr(self):
        return pyobj_repr

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
        hop.exception_is_here()
        v = hop.genop(opname, vlist, resulttype=pyobj_repr)
        if not isinstance(hop.r_result, VoidRepr):
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

    
class __extend__(pairtype(PyObjRepr, PyObjRepr)): 
    def rtype_contains((r_seq, r_item), hop):
        v_seq, v_item = hop.inputargs(r_seq, r_item)
        return hop.llops.gencapicall('PySequence_Contains_with_exc',
                                     [v_seq, v_item], resulttype=Bool)
