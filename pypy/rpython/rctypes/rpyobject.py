from pypy.tool.pairtype import pairtype
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes.rmodel import CTypesValueRepr
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython import extregistry


class CTypesPyObjRepr(CTypesValueRepr):

    def convert_const(self, value):
        if value is None:
            return lltype.nullptr(self.lowleveltype.TO)
        else:
            return super(CTypesPyObjRepr, self).convert_const(value)

    def initialize_const(self, p, value):
        if isinstance(value, self.ctype):
            value = value.value
        if extregistry.is_registered(value):
            entry = extregistry.lookup(value)
            if hasattr(entry, 'get_ll_pyobjectptr'):
                p.c_data[0] = entry.get_ll_pyobjectptr(self.rtyper)
                return
        p.c_data[0] = lltype.pyobjectptr(value)

    def rtype_getattr(self, hop):
        # only for 'allow_someobjects' annotations
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_pyobj = hop.inputarg(self, 0)
        hop.exception_cannot_occur()
        return self.getvalue(hop.llops, v_pyobj)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_pyobj, v_attr, v_newvalue = hop.inputargs(self, lltype.Void,
                                                    pyobj_repr)
        self.setvalue(hop.llops, v_pyobj, v_newvalue)

    def rtype_is_true(self, hop):
        [v_box] = hop.inputargs(self)
        return hop.gendirectcall(ll_pyobjbox_is_true, v_box)

def ll_pyobjbox_is_true(box):
    return bool(box) and bool(box.c_data[0])


class __extend__(pairtype(CTypesPyObjRepr, PyObjRepr)):
    # conversion used by wrapper.py in genc when returning a py_object
    # from a function exposed in a C extension module
    def convert_from_to((r_from, r_to), v, llops):
        return r_from.getvalue(llops, v)

class __extend__(pairtype(PyObjRepr, CTypesPyObjRepr)):
    # conversion used by wrapper.py in genc when passing a py_object
    # argument into a function exposed in a C extension module
    def convert_from_to((r_from, r_to), v, llops):
        # allocate a memory-owning box to hold a copy of the 'PyObject*'
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setvalue(llops, v_owned_box, v)
        # return this box possibly converted to the expected output repr,
        # which might be a memory-aliasing box
        return llops.convertvar(v_owned_box, r_temp, r_to)
