import ctypes

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.lltype import Ptr, FuncType, Void
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import Wrappable
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.cpyext.api import cpython_api, cpython_api_c, cpython_struct
from pypy.module.cpyext.api import PyObject, PyVarObjectFields, Py_ssize_t
from pypy.module.cpyext.api import Py_TPFLAGS_READYING, Py_TPFLAGS_READY
from pypy.interpreter.module import Module
from pypy.module.cpyext.modsupport import PyMethodDef, convert_method_defs
from pypy.module.cpyext.state import State
from pypy.module.cpyext.methodobject import from_ref_ex, generic_cpy_call


PyTypeObject = lltype.ForwardReference()
PyTypeObjectPtr = lltype.Ptr(PyTypeObject)
PyCFunction = Ptr(FuncType([PyObject, PyObject], PyObject))
P, FT, PyO = Ptr, FuncType, PyObject
PyOPtr = Ptr(lltype.Array(PyO, hints={'nolength': True}))


# XXX
PyNumberMethods = PySequenceMethods = PyMappingMethods = \
                  PyBufferProcs = PyMemberDef = rffi.VOIDP.TO

freefunc = P(FT([rffi.VOIDP], Void))
destructor = P(FT([PyO], Void))
printfunc = P(FT([PyO, rffi.VOIDP, rffi.INT_real], rffi.INT))
getattrfunc = P(FT([PyO, rffi.CCHARP], PyO))
getattrofunc = P(FT([PyO, PyO], PyO))
setattrfunc = P(FT([PyO, rffi.CCHARP, PyO], rffi.INT_real))
setattrofunc = P(FT([PyO, PyO, PyO], rffi.INT_real))
cmpfunc = P(FT([PyO, PyO], rffi.INT_real))
reprfunc = P(FT([PyO], PyO))
hashfunc = P(FT([PyO], lltype.Signed))
richcmpfunc = P(FT([PyO, PyO, rffi.INT_real], PyO))
getiterfunc = P(FT([PyO], PyO))
iternextfunc = P(FT([PyO], PyO))
descrgetfunc = P(FT([PyO, PyO, PyO], PyO))
descrsetfunc = P(FT([PyO, PyO, PyO], rffi.INT_real))
initproc = P(FT([PyO, PyO, PyO], rffi.INT_real))
newfunc = P(FT([PyTypeObjectPtr, PyO, PyO], PyO))
allocfunc = P(FT([PyTypeObjectPtr, Py_ssize_t], PyO))
unaryfunc = P(FT([PyO], PyO))
binaryfunc = P(FT([PyO, PyO], PyO))
ternaryfunc = P(FT([PyO, PyO, PyO], PyO))
inquiry = P(FT([PyO], rffi.INT_real))
lenfunc = P(FT([PyO], Py_ssize_t))
coercion = P(FT([PyOPtr, PyOPtr], rffi.INT_real))
intargfunc = P(FT([PyO, rffi.INT_real], PyO))
intintargfunc = P(FT([PyO, rffi.INT_real, rffi.INT], PyO))
ssizeargfunc = P(FT([PyO, Py_ssize_t], PyO))
ssizessizeargfunc = P(FT([PyO, Py_ssize_t, Py_ssize_t], PyO))
intobjargproc = P(FT([PyO, rffi.INT_real, PyO], rffi.INT))
intintobjargproc = P(FT([PyO, rffi.INT_real, rffi.INT, PyO], rffi.INT))
ssizeobjargproc = P(FT([PyO, Py_ssize_t, PyO], rffi.INT_real))
ssizessizeobjargproc = P(FT([PyO, Py_ssize_t, Py_ssize_t, PyO], rffi.INT_real))
objobjargproc = P(FT([PyO, PyO, PyO], rffi.INT_real))

objobjproc = P(FT([PyO, PyO], rffi.INT_real))
visitproc = P(FT([PyO, rffi.VOIDP], rffi.INT_real))
traverseproc = P(FT([PyO, visitproc, rffi.VOIDP], rffi.INT_real))

getter = P(FT([PyO, rffi.VOIDP_real], PyO))
setter = P(FT([PyO, PyO, rffi.VOIDP_real], rffi.INT_real))

PyGetSetDef = cpython_struct("PyGetSetDef", (
    ("name", rffi.CCHARP),
    ("get", getter),
    ("set", setter),
    ("doc", rffi.CCHARP),
    ("closure", rffi.VOIDP_real),
))

PyTypeObjectFields = []
PyTypeObjectFields.extend(PyVarObjectFields)
PyTypeObjectFields.extend([
    ("tp_name", rffi.CCHARP), # For printing, in format "<module>.<name>"
    ("tp_basicsize", Py_ssize_t), ("tp_itemsize", Py_ssize_t), # For allocation

    # Methods to implement standard operations
    ("tp_dealloc", destructor),
    ("tp_print", printfunc),
    ("tp_getattr", getattrfunc),
    ("tp_setattr", setattrfunc),
    ("tp_compare", cmpfunc),
    ("tp_repr", reprfunc),

    # Method suites for standard classes
    ("tp_as_number", Ptr(PyNumberMethods)),
    ("tp_as_sequence", Ptr(PySequenceMethods)),
    ("tp_as_mapping", Ptr(PyMappingMethods)),

    # More standard operations (here for binary compatibility)
    ("tp_hash", hashfunc),
    ("tp_call", ternaryfunc),
    ("tp_str", reprfunc),
    ("tp_getattro", getattrofunc),
    ("tp_setattro", setattrofunc),

    # Functions to access object as input/output buffer
    ("tp_as_buffer", Ptr(PyBufferProcs)),

    # Flags to define presence of optional/expanded features
    ("tp_flags", lltype.Signed),

    ("tp_doc", rffi.CCHARP), # Documentation string

    # Assigned meaning in release 2.0
    # call function for all accessible objects
    ("tp_traverse", traverseproc),

    # delete references to contained objects
    ("tp_clear", inquiry),

    # Assigned meaning in release 2.1
    # rich comparisons 
    ("tp_richcompare", richcmpfunc),

    # weak reference enabler
    ("tp_weaklistoffset", Py_ssize_t),

    # Added in release 2.2
    # Iterators
    ("tp_iter", getiterfunc),
    ("tp_iternext", iternextfunc),

    # Attribute descriptor and subclassing stuff
    ("tp_methods", Ptr(PyMethodDef)),
    ("tp_members", Ptr(PyMemberDef)),
    ("tp_getset", Ptr(PyGetSetDef)),
    ("tp_base", Ptr(PyTypeObject)),
    ("tp_dict", PyObject),
    ("tp_descr_get", descrgetfunc),
    ("tp_descr_set", descrsetfunc),
    ("tp_dictoffset", Py_ssize_t),  # can be ignored in PyPy
    ("tp_init", initproc),
    ("tp_alloc", allocfunc),
    ("tp_new", newfunc),
    ("tp_free", freefunc), # Low-level free-memory routine
    ("tp_is_gc", inquiry), # For PyObject_IS_GC
    ("tp_bases", PyObject),
    ("tp_mro", PyObject), # method resolution order
    ("tp_cache", PyObject),
    ("tp_subclasses", PyObject),
    ("tp_weaklist", PyObject),
    ("tp_del", destructor),
    ])
cpython_struct("PyTypeObject", PyTypeObjectFields, PyTypeObject)



class W_GetSetPropertyEx(GetSetProperty): # XXX fix this to be rpython
    def getter(self, space, w_self):
        return generic_cpy_call(space, self.getset.c_get, w_self, self.getset.c_closure)

    def setter(self, space, w_self, w_value):
        return generic_cpy_call(space, self.getset.c_set, w_self, w_value,
                self.getset.c_closure)

    def __init__(self, getset):
        self.getset = getset
        self.name = rffi.charp2str(getset.c_name)
        doc = set = get = None
        if doc:
            doc = rffi.charp2str(getset.c_doc)
        if getset.c_get:
            get = self.getter.im_func
        if getset.c_set:
            set = self.setter.im_func
        GetSetProperty.__init__(self, get, set, None, doc, W_PyCObject, True)

def PyDescr_NewGetSet(space, getset, pto):
    return space.wrap(W_GetSetPropertyEx(getset))

def convert_getset_defs(space, dict_w, getsets, pto):
    getsets = rffi.cast(rffi.CArrayPtr(PyGetSetDef), getsets)
    if getsets:
        i = -1
        while True:
            i = i + 1
            getset = getsets[i]
            name = getset.c_name
            if not name:
                break
            name = rffi.charp2str(name)
            w_descr = PyDescr_NewGetSet(space, getset, pto)
            dict_w[name] = w_descr


class W_PyCTypeObject(W_TypeObject):
    def __init__(self, space, pto):
        self.pto = pto
        bases_w = []
        dict_w = {}
        convert_method_defs(space, dict_w, pto.c_tp_methods, pto)
        convert_getset_defs(space, dict_w, pto.c_tp_getset, pto)
        W_TypeObject.__init__(self, space, rffi.charp2str(pto.c_tp_name),
            bases_w or [space.w_object], dict_w)

class W_PyCObject(Wrappable):
    pass

@unwrap_spec(ObjSpace, W_Root, W_Root)
def cobject_descr_getattr(space, w_obj, w_name):
    name = space.str_w(w_name)
    return w_name


def allocate_type_obj(space, w_obj):
    pto = lltype.malloc(PyTypeObject, None, flavor="raw")
    #  XXX fill slots in pto
    return pto

def create_type_object(space, pto):
    w_type = space.allocate_instance(W_PyCTypeObject, space.gettypeobject(W_PyCTypeObject.typedef))
    w_type.__init__(space, pto)
    w_type.ready()
    return w_type

@cpython_api_c()
def PyType_Ready(space, pto):
    "Implemented in typeobject.c"

@cpython_api([PyTypeObjectPtr], rffi.INT_real)
def PyPyType_Register(space, pto):
    state = space.fromcache(State)
    ptr = ctypes.addressof(pto._obj._storage)
    if ptr not in state.py_objects_r2w:
        w_obj = create_type_object(space, pto)
        state.py_objects_r2w[ptr] = w_obj
        state.py_objects_w2r[w_obj] = pto
    return 1

W_PyCObject.typedef = W_ObjectObject.typedef
#TypeDef(
#    'C_object',
#    #__getattrbute__ = interp2app(cobject_descr_getattribute),
#    )

W_PyCTypeObject.typedef = TypeDef(
    'C_type', W_TypeObject.typedef
    )
