from ctypes import py_object
from pypy.annotation.model import SomeCTypesObject, SomeImpossibleValue
from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.rpython.lltypesystem import lltype
from pypy.tool.uid import Hashable


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

##    def object_seen(self, bookkeeper):
##        "Called when the annotator sees this py_object."
##        # extension: if the py_object instance has a 'builder' attribute,
##        # it must be a pair (callable, args) which is meant to be called
##        # at initialization-time when the compiled extension module is
##        # first imported.  It returns the "real" Python object.
##        if hasattr(self.instance, 'builder'):
##            # emulate a call so that the callable is properly annotated
##            callable, args = self.instance.builder
##            s_callable = bookkeeper.immutablevalue(callable)
##            args_s = [bookkeeper.immutablevalue(a) for a in args]
##            uniquekey = Hashable(self.instance)
##            s_res = bookkeeper.emulate_pbc_call(uniquekey, s_callable, args_s)
##            assert (issubclass(s_res.knowntype, py_object) or
##                    isinstance(s_res, SomeImpossibleValue))

    def get_repr(self, rtyper, s_pyobject):
        from pypy.rpython.rctypes.rpyobject import CTypesPyObjRepr
        lowleveltype = lltype.Ptr(lltype.PyObject)
        return CTypesPyObjRepr(rtyper, s_pyobject, lowleveltype)


def register_py_object_subclass(subcls):
    assert issubclass(subcls, py_object)
    CallEntry._register_value(subcls)
    ObjEntry._register_type(subcls)
