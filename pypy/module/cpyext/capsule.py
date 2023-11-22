from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import (bootstrap_function, slot_function,
    PyObject, build_type_checkers, cts, parse_dir)
from pypy.module.cpyext.pyobject import (make_ref, from_ref,
    make_typedescr, track_reference)
from pypy.interpreter.error import oefmt
from pypy.objspace.std.capsuleobject import W_Capsule

cts.parse_header(parse_dir / 'cpyext_capsule.h')
PyCapsule = cts.gettype("PyCapsule")

@bootstrap_function
def init_capsuleobject(space):
    "Type description of PyCapsuleobject"
    make_typedescr(W_Capsule.typedef,
                   basestruct=PyCapsule,
                   attach=capsule_attach,
                   realize=capsule_realize,
                   dealloc=capsule_dealloc,
                  )

def capsule_attach(space, py_obj, w_obj, w_userdata=None):
    """
    Fills a newly allocated PyCapsule with the given capsule object. The
    value must only be modified through PyCapsule_Set interfaces
    """
    assert isinstance(w_obj, W_Capsule)
    pycapsule_obj = cts.cast("PyCapsule*", py_obj)
    pycapsule_obj.c_pointer = w_obj.pointer
    pycapsule_obj.c_name = w_obj.name
    pycapsule_obj.c_context = w_obj.context

def capsule_realize(space, obj):
    # Allocate and fill a w_obj from a pyobj
    py_obj = cts.cast("PyCapsule*", obj)
    w_obj = W_Capsule(space, py_obj.c_pointer, py_obj.c_name)
    w_obj.context = py_obj.c_context
    track_reference(space, obj, w_obj)
    return w_obj

@slot_function([PyObject], lltype.Void)
def capsule_dealloc(space, py_obj):
    """Frees allocated PyBytesObject resources.
    """
    from pypy.module.cpyext.object import _dealloc
    py_capsule = cts.cast("PyCapsule *", py_obj)
    if py_capsule.c_destructor:
        py_capsule.c_destructor(py_obj)
    _dealloc(space, py_obj)

@cts.decl("""PyObject *
    PyCapsule_New(void *pointer, const char *name, PyCapsule_Destructor destructor)""",
    result_is_ll=True)
def PyCapsule_New(space, pointer, name, destructor):
    if not pointer:
        raise oefmt(space.w_ValueError, "PyCapsule_New called with null pointer")
    w_obj = W_Capsule(space, pointer, name)
    pyobj = cts.cast("PyCapsule *", make_ref(space, w_obj))
    pyobj.c_destructor = destructor
    return pyobj

@cts.decl("int PyCapsule_SetPointer(PyObject *capsule, void *pointer)", error=-1)
def PyCapsule_SetPointer(space, py_obj, pointer):
    # Set both the capsule and the w_obj. We can't use the attach/realize
    # mechanism since this is in-place modification
    py_capsule = cts.cast("PyCapsule*", py_obj)
    py_capsule.c_pointer = pointer
    w_obj = from_ref(space, py_obj)
    assert isinstance(w_obj, W_Capsule)
    w_obj.pointer = pointer
    return 0

@cts.decl("int PyCapsule_SetDestructor(PyObject *capsule, PyCapsule_Destructor destructor)", error=-1)
def PyCapsule_SetDestructor(space, py_obj, destructor):
    # Set both the capsule and the w_obj. We can't use the attach/realize
    # mechanism since this is in-place modification
    py_capsule = cts.cast("PyCapsule*", py_obj)
    py_capsule.c_destructor = destructor
    return 0

@cts.decl("int PyCapsule_SetName(PyObject *capsule, const char *name)", error=-1)
def PyCapsule_SetName(space, py_obj, name):
    # Set both the capsule and the w_obj. We can't use the attach/realize
    # mechanism since this is in-place modification
    py_capsule = cts.cast("PyCapsule*", py_obj)
    py_capsule.c_name = name
    w_obj = from_ref(space, py_obj)
    assert isinstance(w_obj, W_Capsule)
    w_obj.name = name
    return 0

@cts.decl("int PyCapsule_SetContext(PyObject *capsule, void *context)", error=-1)
def PyCapsule_SetContext(space, py_obj, context):
    # Set both the capsule and the w_obj. We can't use the attach/realize
    # mechanism since this is in-place modification
    py_capsule = cts.cast("PyCapsule*", py_obj)
    py_capsule.c_context = context
    w_obj = from_ref(space, py_obj)
    assert isinstance(w_obj, W_Capsule)
    w_obj.context = context
    return 0
