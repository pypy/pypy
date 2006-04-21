from ctypes import py_object
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.rpython.lltypesystem import lltype


class CallEntry(CTypesCallEntry):
    "Annotation and rtyping of calls to py_object."
    _about_ = py_object

    def specialize_call(self, hop):
        from pypy.rpython.robject import pyobj_repr
        r_pyobject = hop.r_result
        v_result = r_pyobject.allocate_instance(hop.llops)
        if len(hop.args_s):
            [v_input] = hop.inputargs(pyobj_repr)
            r_pyobject.setvalue(hop.llops, v_result, v_input)
        return v_result


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of py_object instances."
    _type_ = py_object

    def get_repr(self, rtyper, s_pyobject):
        from pypy.rpython.rctypes.rpyobject import CTypesPyObjRepr
        lowleveltype = lltype.Ptr(lltype.PyObject)
        return CTypesPyObjRepr(rtyper, s_pyobject, lowleveltype)
