from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    PyObjectFields, generic_cpy_call, CONST_STRING,
    cpython_api, bootstrap_function, cpython_struct, build_type_checkers)
from pypy.module.cpyext.pyobject import (
    PyObject, make_ref, from_ref, Py_DecRef, make_typedescr, borrow_from)
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Function, Method
from pypy.interpreter.pycode import PyCode

PyFunctionObjectStruct = lltype.ForwardReference()
PyFunctionObject = lltype.Ptr(PyFunctionObjectStruct)
PyFunctionObjectFields = PyObjectFields + \
    (("func_name", PyObject),)
cpython_struct("PyFunctionObject", PyFunctionObjectFields, PyFunctionObjectStruct)

@bootstrap_function
def init_functionobject(space):
    make_typedescr(Function.typedef,
                   basestruct=PyFunctionObject.TO,
                   attach=function_attach,
                   dealloc=function_dealloc)

PyFunction_Check, PyFunction_CheckExact = build_type_checkers("Function", Function)
PyMethod_Check, PyMethod_CheckExact = build_type_checkers("Method", Method)

def function_attach(space, py_obj, w_obj):
    py_func = rffi.cast(PyFunctionObject, py_obj)
    assert isinstance(w_obj, Function)
    py_func.c_func_name = make_ref(space, space.wrap(w_obj.name))

@cpython_api([PyObject], lltype.Void, external=False)
def function_dealloc(space, py_obj):
    py_func = rffi.cast(PyFunctionObject, py_obj)
    Py_DecRef(space, py_func.c_func_name)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyMethod_New(space, w_func, w_self, w_cls):
    """Return a new method object, with func being any callable object; this is the
    function that will be called when the method is called.  If this method should
    be bound to an instance, self should be the instance and class should be the
    class of self, otherwise self should be NULL and class should be the
    class which provides the unbound method."""
    return Method(space, w_func, w_self, w_cls)

@cpython_api([PyObject], PyObject)
def PyMethod_Function(space, w_method):
    """Return the function object associated with the method meth."""
    assert isinstance(w_method, Method)
    return borrow_from(w_method, w_method.w_function)

@cpython_api([PyObject], PyObject)
def PyMethod_Self(space, w_method):
    """Return the instance associated with the method meth if it is bound,
    otherwise return NULL."""
    assert isinstance(w_method, Method)
    return borrow_from(w_method, w_method.w_instance)

@cpython_api([PyObject], PyObject)
def PyMethod_Class(space, w_method):
    """Return the class object from which the method meth was created; if this was
    created from an instance, it will be the class of the instance."""
    assert isinstance(w_method, Method)
    return borrow_from(w_method, w_method.w_class)

@cpython_api([CONST_STRING, CONST_STRING, rffi.INT_real], PyObject)
def PyCode_NewEmpty(space, filename, funcname, firstlineno):
    """Creates a new empty code object with the specified source location."""
    raise OperationError(space.w_NotImplementedError, space.wrap(
        "PyCode_NewEmpty"))
    # XXX I keep getting a "TooLateForChange" around the annotation of
    # the consts variable
    return space.wrap(PyCode(space,
                             argcount=0,
                             nlocals=0,
                             stacksize=0,
                             flags=0,
                             code="",
                             consts=list([]),
                             names=[],
                             varnames=[],
                             filename=rffi.charp2str(filename),
                             name=rffi.charp2str(funcname),
                             firstlineno=firstlineno,
                             lnotab="",
                             freevars=[],
                             cellvars=[]))

