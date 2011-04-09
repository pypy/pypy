from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.lltype import Ptr, FuncType, Void
from pypy.module.cpyext.api import (cpython_struct, Py_ssize_t, Py_ssize_tP,
    PyVarObjectFields, PyTypeObject, PyTypeObjectPtr, FILEP,
    Py_TPFLAGS_READYING, Py_TPFLAGS_READY, Py_TPFLAGS_HEAPTYPE)
from pypy.module.cpyext.pyobject import PyObject, make_ref, from_ref
from pypy.module.cpyext.modsupport import PyMethodDef


P, FT, PyO = Ptr, FuncType, PyObject
PyOPtr = Ptr(lltype.Array(PyO, hints={'nolength': True}))

freefunc = P(FT([rffi.VOIDP], Void))
destructor = P(FT([PyO], Void))
printfunc = P(FT([PyO, FILEP, rffi.INT_real], rffi.INT))
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

getter = P(FT([PyO, rffi.VOIDP], PyO))
setter = P(FT([PyO, PyO, rffi.VOIDP], rffi.INT_real))

wrapperfunc = P(FT([PyO, PyO, rffi.VOIDP], PyO))
wrapperfunc_kwds = P(FT([PyO, PyO, rffi.VOIDP, PyO], PyO))

readbufferproc = P(FT([PyO, Py_ssize_t, rffi.VOIDPP], Py_ssize_t))
writebufferproc = P(FT([PyO, Py_ssize_t, rffi.VOIDPP], Py_ssize_t))
segcountproc = P(FT([PyO, Py_ssize_tP], Py_ssize_t))
charbufferproc = P(FT([PyO, Py_ssize_t, rffi.CCHARPP], Py_ssize_t))
## We don't support new buffer interface for now
getbufferproc = rffi.VOIDP
releasebufferproc = rffi.VOIDP


PyGetSetDef = cpython_struct("PyGetSetDef", (
    ("name", rffi.CCHARP),
    ("get", getter),
    ("set", setter),
    ("doc", rffi.CCHARP),
    ("closure", rffi.VOIDP),
))

PyNumberMethods = cpython_struct("PyNumberMethods", (
    ("nb_add", binaryfunc),
    ("nb_subtract", binaryfunc),
    ("nb_multiply", binaryfunc),
    ("nb_divide", binaryfunc),
    ("nb_remainder", binaryfunc),
    ("nb_divmod", binaryfunc),
    ("nb_power", ternaryfunc),
    ("nb_negative", unaryfunc),
    ("nb_positive", unaryfunc),
    ("nb_absolute", unaryfunc),
    ("nb_nonzero", inquiry),
    ("nb_invert", unaryfunc),
    ("nb_lshift", binaryfunc),
    ("nb_rshift", binaryfunc),
    ("nb_and", binaryfunc),
    ("nb_xor", binaryfunc),
    ("nb_or", binaryfunc),
    ("nb_coerce", coercion),
    ("nb_int", unaryfunc),
    ("nb_long", unaryfunc),
    ("nb_float", unaryfunc),
    ("nb_oct", unaryfunc),
    ("nb_hex", unaryfunc),
    ("nb_inplace_add", binaryfunc),
    ("nb_inplace_subtract", binaryfunc),
    ("nb_inplace_multiply", binaryfunc),
    ("nb_inplace_divide", binaryfunc),
    ("nb_inplace_remainder", binaryfunc),
    ("nb_inplace_power", ternaryfunc),
    ("nb_inplace_lshift", binaryfunc),
    ("nb_inplace_rshift", binaryfunc),
    ("nb_inplace_and", binaryfunc),
    ("nb_inplace_xor", binaryfunc),
    ("nb_inplace_or", binaryfunc),

    ("nb_floor_divide", binaryfunc),
    ("nb_true_divide", binaryfunc),
    ("nb_inplace_floor_divide", binaryfunc),
    ("nb_inplace_true_divide", binaryfunc),

    ("nb_index", unaryfunc),
))

PySequenceMethods = cpython_struct("PySequenceMethods", (
    ("sq_length", lenfunc),
    ("sq_concat", binaryfunc),
    ("sq_repeat", ssizeargfunc),
    ("sq_item", ssizeargfunc),
    ("sq_slice", ssizessizeargfunc),
    ("sq_ass_item", ssizeobjargproc),
    ("sq_ass_slice", ssizessizeobjargproc),
    ("sq_contains", objobjproc),
    ("sq_inplace_concat", binaryfunc),
    ("sq_inplace_repeat", ssizeargfunc),
))

PyMappingMethods = cpython_struct("PyMappingMethods", (
    ("mp_length", lenfunc),
    ("mp_subscript", binaryfunc),
    ("mp_ass_subscript", objobjargproc),
))

PyBufferProcs = cpython_struct("PyBufferProcs", (
    ("bf_getreadbuffer", readbufferproc),
    ("bf_getwritebuffer", writebufferproc),
    ("bf_getsegcount", segcountproc),
    ("bf_getcharbuffer", charbufferproc),
    ("bf_getbuffer", getbufferproc),
    ("bf_releasebuffer", releasebufferproc),
))

PyMemberDef = cpython_struct("PyMemberDef", (
    ("name", rffi.CCHARP),
    ("type",  rffi.INT_real),
    ("offset", Py_ssize_t),
    ("flags", rffi.INT_real),
    ("doc", rffi.CCHARP),
))

# These fields are supported and used in different ways
# The following comments mean:
#    #E    essential, initialized for all PTOs
#    #S    supported
#    #U    unsupported
#    #N    not yet implemented
PyTypeObjectFields = []
PyTypeObjectFields.extend(PyVarObjectFields)
PyTypeObjectFields.extend([
    ("tp_name", rffi.CCHARP), #E For printing, in format "<module>.<name>"
    ("tp_basicsize", Py_ssize_t), #E  For allocation
    ("tp_itemsize", Py_ssize_t),  #E       "

    # Methods to implement standard operations
    ("tp_dealloc", destructor),   #E
    ("tp_print", printfunc),      #U
    ("tp_getattr", getattrfunc),  #U
    ("tp_setattr", setattrfunc),  #U
    ("tp_compare", cmpfunc),      #N
    ("tp_repr", reprfunc),        #N

    # Method suites for standard classes
    ("tp_as_number", Ptr(PyNumberMethods)), #N
    ("tp_as_sequence", Ptr(PySequenceMethods)), #N
    ("tp_as_mapping", Ptr(PyMappingMethods)), #N

    # More standard operations (here for binary compatibility)
    ("tp_hash", hashfunc),        #N
    ("tp_call", ternaryfunc),     #N
    ("tp_str", reprfunc),         #N
    ("tp_getattro", getattrofunc),#N
    ("tp_setattro", setattrofunc),#N

    # Functions to access object as input/output buffer
    ("tp_as_buffer", Ptr(PyBufferProcs)), #U

    # Flags to define presence of optional/expanded features
    ("tp_flags", lltype.Signed),  #E

    ("tp_doc", rffi.CCHARP),      #N Documentation string

    # Assigned meaning in release 2.0
    # call function for all accessible objects
    ("tp_traverse", traverseproc),#U

    # delete references to contained objects
    ("tp_clear", inquiry),        #U

    # Assigned meaning in release 2.1
    # rich comparisons 
    ("tp_richcompare", richcmpfunc), #N

    # weak reference enabler
    ("tp_weaklistoffset", Py_ssize_t), #U

    # Added in release 2.2
    # Iterators
    ("tp_iter", getiterfunc),       #N
    ("tp_iternext", iternextfunc),  #N

    # Attribute descriptor and subclassing stuff
    ("tp_methods", Ptr(PyMethodDef)), #S
    ("tp_members", Ptr(PyMemberDef)), #S
    ("tp_getset", Ptr(PyGetSetDef)),  #S
    ("tp_base", Ptr(PyTypeObject)),   #E
    ("tp_dict", PyObject),            #U
    ("tp_descr_get", descrgetfunc),   #N
    ("tp_descr_set", descrsetfunc),   #N
    ("tp_dictoffset", Py_ssize_t),    #U
    ("tp_init", initproc),            #N
    ("tp_alloc", allocfunc),          #N
    ("tp_new", newfunc),              #S
    ("tp_free", freefunc), #E Low-level free-memory routine
    ("tp_is_gc", inquiry), #U For PyObject_IS_GC
    ("tp_bases", PyObject),#E
    ("tp_mro", PyObject),  #U method resolution order
    ("tp_cache", PyObject),#S
    ("tp_subclasses", PyObject), #U
    ("tp_weaklist", PyObject),   #U
    ("tp_del", destructor),      #N
    ])
cpython_struct("PyTypeObject", PyTypeObjectFields, PyTypeObject)


