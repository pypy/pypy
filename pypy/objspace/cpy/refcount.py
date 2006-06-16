from pypy.annotation import model as annmodel
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.objspace.cpy.capi import *


###################################################################
# ____________________ Reference counter hacks ____________________

_XX_PyObject_GetItem = pythonapi.PyObject_GetItem
_XX_PyObject_GetItem.argtypes = [W_Object, W_Object]
_XX_PyObject_GetItem.restype = None   # !

_XX_PyList_SetItem = pythonapi.PyList_SetItem
_XX_PyList_SetItem.argtypes = [W_Object, Py_ssize_t, W_Object]
_XX_PyList_SetItem.restype = c_int

def Py_Incref(w):
    container = (w.value,)
    _XX_PyObject_GetItem(W_Object(container), W_Object(0))
    # the new reference returned by PyObject_GetItem is ignored and lost

def Py_Decref(w):
    lst = [None]
    # consume a reference
    _XX_PyList_SetItem(W_Object(lst), 0, w)

def Py_XIncref(w):
    if w:
        Py_Incref(w)

def Py_XDecref(w):
    if w:
        Py_Decref(w)


class IncrefFnEntry(ExtRegistryEntry):
    "Annotation and specialization of calls to Py_Incref()."
    _about_ = Py_Incref

    def compute_result_annotation(self, s_arg):
        return annmodel.s_None

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        s_pyobj = annmodel.SomeCTypesObject(W_Object, ownsmemory=False)
        r_pyobj = hop.rtyper.getrepr(s_pyobj)
        [v_box] = hop.inputargs(r_pyobj)
        v_value = r_pyobj.getvalue(hop.llops, v_box)
        hop.genop('gc_push_alive_pyobj', [v_value])
        return hop.inputconst(lltype.Void, None)


class DecrefFnEntry(ExtRegistryEntry):
    "Annotation and specialization of calls to Py_Decref()."
    _about_ = Py_Decref

    def compute_result_annotation(self, s_arg):
        return annmodel.s_None

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        s_pyobj = annmodel.SomeCTypesObject(W_Object, ownsmemory=False)
        r_pyobj = hop.rtyper.getrepr(s_pyobj)
        [v_box] = hop.inputargs(r_pyobj)
        v_value = r_pyobj.getvalue(hop.llops, v_box)
        hop.genop('gc_pop_alive_pyobj', [v_value])
        return hop.inputconst(lltype.Void, None)
