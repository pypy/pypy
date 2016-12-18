from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, bootstrap_function, PyObjectFields, cpython_struct,
    CANNOT_FAIL)
from pypy.module.cpyext.pyobject import (
    PyObject, Py_DecRef, make_ref, from_ref, track_reference,
    make_typedescr, get_typedescr)
from pypy.module.cpyext.state import State
from pypy.module.cpyext.pystate import PyThreadState
from pypy.module.cpyext.funcobject import PyCodeObject
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pytraceback import PyTraceback

PyFrameObjectStruct = lltype.ForwardReference()
PyFrameObject = lltype.Ptr(PyFrameObjectStruct)
PyFrameObjectFields = (PyObjectFields +
    (("f_code", PyCodeObject),
     ("f_globals", PyObject),
     ("f_locals", PyObject),
     ("f_lineno", rffi.INT),
     ))
cpython_struct("PyFrameObject", PyFrameObjectFields, PyFrameObjectStruct)

@bootstrap_function
def init_frameobject(space):
    make_typedescr(PyFrame.typedef,
                   basestruct=PyFrameObject.TO,
                   attach=frame_attach,
                   dealloc=frame_dealloc,
                   realize=frame_realize)

def frame_attach(space, py_obj, w_obj, w_userdata=None):
    "Fills a newly allocated PyFrameObject with a frame object"
    frame = space.interp_w(PyFrame, w_obj)
    py_frame = rffi.cast(PyFrameObject, py_obj)
    py_frame.c_f_code = rffi.cast(PyCodeObject, make_ref(space, frame.pycode))
    py_frame.c_f_globals = make_ref(space, frame.get_w_globals())
    py_frame.c_f_locals = make_ref(space, frame.get_w_locals())
    rffi.setintfield(py_frame, 'c_f_lineno', frame.getorcreatedebug().f_lineno)

@cpython_api([PyObject], lltype.Void, header=None)
def frame_dealloc(space, py_obj):
    py_frame = rffi.cast(PyFrameObject, py_obj)
    py_code = rffi.cast(PyObject, py_frame.c_f_code)
    Py_DecRef(space, py_code)
    Py_DecRef(space, py_frame.c_f_globals)
    Py_DecRef(space, py_frame.c_f_locals)
    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)

def frame_realize(space, py_obj):
    """
    Creates the frame in the interpreter. The PyFrameObject structure must not
    be modified after this call.
    """
    py_frame = rffi.cast(PyFrameObject, py_obj)
    py_code = rffi.cast(PyObject, py_frame.c_f_code)
    w_code = from_ref(space, py_code)
    code = space.interp_w(PyCode, w_code)
    w_globals = from_ref(space, py_frame.c_f_globals)

    frame = space.FrameClass(space, code, w_globals, outer_func=None)
    d = frame.getorcreatedebug()
    d.f_lineno = rffi.getintfield(py_frame, 'c_f_lineno')
    w_obj = space.wrap(frame)
    track_reference(space, py_obj, w_obj)
    return w_obj

@cpython_api([PyThreadState, PyCodeObject, PyObject, PyObject], PyFrameObject,
             result_is_ll=True)
def PyFrame_New(space, tstate, w_code, w_globals, w_locals):
    typedescr = get_typedescr(PyFrame.typedef)
    py_obj = typedescr.allocate(space, space.gettypeobject(PyFrame.typedef))
    py_frame = rffi.cast(PyFrameObject, py_obj)
    space.interp_w(PyCode, w_code) # sanity check
    py_frame.c_f_code = rffi.cast(PyCodeObject, make_ref(space, w_code))
    py_frame.c_f_globals = make_ref(space, w_globals)
    py_frame.c_f_locals = make_ref(space, w_locals)
    return py_frame

@cpython_api([PyFrameObject], rffi.INT_real, error=-1)
def PyTraceBack_Here(space, w_frame):
    from pypy.interpreter.pytraceback import record_application_traceback
    state = space.fromcache(State)
    if state.operror is None:
        return -1
    frame = space.interp_w(PyFrame, w_frame)
    record_application_traceback(space, state.operror, frame, 0)
    return 0

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyTraceBack_Check(space, w_obj):
    return isinstance(w_obj, PyTraceback)
