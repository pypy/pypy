import sys

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root, SpaceCache
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.extregistry import ExtRegistryEntry
from pypy.module.cpyext.api import (
    cpython_api, bootstrap_function, PyObject, PyObjectP, ADDR,
    CANNOT_FAIL, Py_TPFLAGS_HEAPTYPE, PyTypeObjectPtr, is_PyObject,
    PyVarObject)
from pypy.module.cpyext.state import State
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.std.objectobject import W_ObjectObject
from rpython.rlib.objectmodel import specialize
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import rawrefcount
from rpython.rlib.debug import fatalerror


#________________________________________________________
# type description

class BaseCpyTypedescr(object):
    basestruct = PyObject.TO
    W_BaseObject = W_ObjectObject

    def get_dealloc(self):
        from pypy.module.cpyext.typeobject import subtype_dealloc
        return subtype_dealloc.api_func

    def allocate(self, space, w_type, itemcount=0):
        # typically called from PyType_GenericAlloc via typedescr.allocate
        # this returns a PyObject with ob_refcnt == 1.

        pytype = as_pyobj(space, w_type)
        pytype = rffi.cast(PyTypeObjectPtr, pytype)
        assert pytype
        # Don't increase refcount for non-heaptypes
        flags = rffi.cast(lltype.Signed, pytype.c_tp_flags)
        if flags & Py_TPFLAGS_HEAPTYPE:
            Py_IncRef(space, w_type)

        if pytype:
            size = pytype.c_tp_basicsize
        else:
            size = rffi.sizeof(self.basestruct)
        if pytype.c_tp_itemsize:
            size += itemcount * pytype.c_tp_itemsize
        assert size >= rffi.sizeof(PyObject.TO)
        buf = lltype.malloc(rffi.VOIDP.TO, size,
                            flavor='raw', zero=True,
                            add_memory_pressure=True)
        pyobj = rffi.cast(PyObject, buf)
        if pytype.c_tp_itemsize:
            pyvarobj = rffi.cast(PyVarObject, pyobj)
            pyvarobj.c_ob_size = itemcount
        pyobj.c_ob_refcnt = 1
        #pyobj.c_ob_pypy_link should get assigned very quickly
        pyobj.c_ob_type = pytype
        return pyobj

    def attach(self, space, pyobj, w_obj, w_userdata=None):
        pass

    def realize(self, space, obj):
        w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
        try:
            w_obj = space.allocate_instance(self.W_BaseObject, w_type)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise oefmt(space.w_SystemError,
                            "cpyext: don't know how to make a '%N' object "
                            "from a PyObject",
                            w_type)
            raise
        track_reference(space, obj, w_obj)
        return w_obj

typedescr_cache = {}

def make_typedescr(typedef, **kw):
    """NOT_RPYTHON

    basestruct: The basic structure to allocate
    alloc     : allocate and basic initialization of a raw PyObject
    attach    : Function called to tie a raw structure to a pypy object
    realize   : Function called to create a pypy object from a raw struct
    dealloc   : a @slot_function(), similar to PyObject_dealloc
    """

    tp_basestruct = kw.pop('basestruct', PyObject.TO)
    tp_alloc      = kw.pop('alloc', None)
    tp_attach     = kw.pop('attach', None)
    tp_realize    = kw.pop('realize', None)
    tp_dealloc    = kw.pop('dealloc', None)
    assert not kw, "Extra arguments to make_typedescr"

    null_dealloc = lltype.nullptr(lltype.FuncType([PyObject], lltype.Void))

    class CpyTypedescr(BaseCpyTypedescr):
        basestruct = tp_basestruct

        if tp_alloc:
            def allocate(self, space, w_type, itemcount=0):
                return tp_alloc(space, w_type, itemcount)

        if tp_dealloc:
            def get_dealloc(self):
                return tp_dealloc.api_func

        if tp_attach:
            def attach(self, space, pyobj, w_obj, w_userdata=None):
                tp_attach(space, pyobj, w_obj, w_userdata)

        if tp_realize:
            def realize(self, space, ref):
                return tp_realize(space, ref)
    if typedef:
        CpyTypedescr.__name__ = "CpyTypedescr_%s" % (typedef.name,)

    typedescr_cache[typedef] = CpyTypedescr()

@bootstrap_function
def init_pyobject(space):
    from pypy.module.cpyext.object import PyObject_dealloc
    # typedescr for the 'object' type
    make_typedescr(space.w_object.layout.typedef,
                   dealloc=PyObject_dealloc)
    # almost all types, which should better inherit from object.
    make_typedescr(None)

@specialize.memo()
def _get_typedescr_1(typedef):
    try:
        return typedescr_cache[typedef]
    except KeyError:
        if typedef.bases:
            return _get_typedescr_1(typedef.bases[0])
        return typedescr_cache[None]

def get_typedescr(typedef):
    if typedef is None:
        return typedescr_cache[None]
    else:
        return _get_typedescr_1(typedef)

#________________________________________________________
# refcounted object support

class InvalidPointerException(Exception):
    pass

def create_ref(space, w_obj, w_userdata=None):
    """
    Allocates a PyObject, and fills its fields with info from the given
    interpreter object.
    """
    w_type = space.type(w_obj)
    pytype = rffi.cast(PyTypeObjectPtr, as_pyobj(space, w_type))
    typedescr = get_typedescr(w_obj.typedef)
    if pytype.c_tp_itemsize != 0:
        itemcount = space.len_w(w_obj) # PyBytesObject and subclasses
    else:
        itemcount = 0
    py_obj = typedescr.allocate(space, w_type, itemcount=itemcount)
    track_reference(space, py_obj, w_obj)
    #
    # py_obj.c_ob_refcnt should be exactly REFCNT_FROM_PYPY + 1 here,
    # and we want only REFCNT_FROM_PYPY, i.e. only count as attached
    # to the W_Root but not with any reference from the py_obj side.
    assert py_obj.c_ob_refcnt > rawrefcount.REFCNT_FROM_PYPY
    py_obj.c_ob_refcnt -= 1
    #
    typedescr.attach(space, py_obj, w_obj, w_userdata)
    return py_obj

def track_reference(space, py_obj, w_obj):
    """
    Ties together a PyObject and an interpreter object.
    The PyObject's refcnt is increased by REFCNT_FROM_PYPY.
    The reference in 'py_obj' is not stolen!  Remember to Py_DecRef()
    it is you need to.
    """
    # XXX looks like a PyObject_GC_TRACK
    assert py_obj.c_ob_refcnt < rawrefcount.REFCNT_FROM_PYPY
    py_obj.c_ob_refcnt += rawrefcount.REFCNT_FROM_PYPY
    rawrefcount.create_link_pypy(w_obj, py_obj)


w_marker_deallocating = W_Root()

def from_ref(space, ref):
    """
    Finds the interpreter object corresponding to the given reference.  If the
    object is not yet realized (see bytesobject.py), creates it.
    """
    assert is_pyobj(ref)
    if not ref:
        return None
    w_obj = rawrefcount.to_obj(W_Root, ref)
    if w_obj is not None:
        if w_obj is not w_marker_deallocating:
            return w_obj
        fatalerror(
            "*** Invalid usage of a dying CPython object ***\n"
            "\n"
            "cpyext, the emulation layer, detected that while it is calling\n"
            "an object's tp_dealloc, the C code calls back a function that\n"
            "tries to recreate the PyPy version of the object.  Usually it\n"
            "means that tp_dealloc calls some general PyXxx() API.  It is\n"
            "a dangerous and potentially buggy thing to do: even in CPython\n"
            "the PyXxx() function could, in theory, cause a reference to the\n"
            "object to be taken and stored somewhere, for an amount of time\n"
            "exceeding tp_dealloc itself.  Afterwards, the object will be\n"
            "freed, making that reference point to garbage.\n"
            ">>> PyPy could contain some workaround to still work if\n"
            "you are lucky, but it is not done so far; better fix the bug in\n"
            "the CPython extension.")

    # This reference is not yet a real interpreter object.
    # Realize it.
    ref_type = rffi.cast(PyObject, ref.c_ob_type)
    if ref_type == ref: # recursion!
        raise InvalidPointerException(str(ref))
    w_type = from_ref(space, ref_type)
    assert isinstance(w_type, W_TypeObject)
    return get_typedescr(w_type.layout.typedef).realize(space, ref)

def as_pyobj(space, w_obj, w_userdata=None):
    """
    Returns a 'PyObject *' representing the given intepreter object.
    This doesn't give a new reference, but the returned 'PyObject *'
    is valid at least as long as 'w_obj' is.  **To be safe, you should
    use keepalive_until_here(w_obj) some time later.**  In case of
    doubt, use the safer make_ref().
    """
    if w_obj is not None:
        assert not is_pyobj(w_obj)
        py_obj = rawrefcount.from_obj(PyObject, w_obj)
        if not py_obj:
            py_obj = create_ref(space, w_obj, w_userdata)
        return py_obj
    else:
        return lltype.nullptr(PyObject.TO)
as_pyobj._always_inline_ = 'try'

def pyobj_has_w_obj(pyobj):
    w_obj = rawrefcount.to_obj(W_Root, pyobj)
    return w_obj is not None and w_obj is not w_marker_deallocating


def is_pyobj(x):
    if x is None or isinstance(x, W_Root):
        return False
    elif is_PyObject(lltype.typeOf(x)):
        return True
    else:
        raise TypeError(repr(type(x)))

class Entry(ExtRegistryEntry):
    _about_ = is_pyobj
    def compute_result_annotation(self, s_x):
        from rpython.rtyper.llannotation import SomePtr
        return self.bookkeeper.immutablevalue(isinstance(s_x, SomePtr))
    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Bool, hop.s_result.const)

@specialize.ll()
def make_ref(space, obj, w_userdata=None):
    """Increment the reference counter of the PyObject and return it.
    Can be called with either a PyObject or a W_Root.
    """
    if is_pyobj(obj):
        pyobj = rffi.cast(PyObject, obj)
    else:
        pyobj = as_pyobj(space, obj, w_userdata)
    if pyobj:
        assert pyobj.c_ob_refcnt > 0
        pyobj.c_ob_refcnt += 1
        if not is_pyobj(obj):
            keepalive_until_here(obj)
    return pyobj


@specialize.ll()
def get_w_obj_and_decref(space, obj):
    """Decrement the reference counter of the PyObject and return the
    corresponding W_Root object (so the reference count is at least
    REFCNT_FROM_PYPY and cannot be zero).  Can be called with either
    a PyObject or a W_Root.
    """
    if is_pyobj(obj):
        pyobj = rffi.cast(PyObject, obj)
        w_obj = from_ref(space, pyobj)
    else:
        w_obj = obj
        pyobj = as_pyobj(space, w_obj)
    if pyobj:
        pyobj.c_ob_refcnt -= 1
        assert pyobj.c_ob_refcnt >= rawrefcount.REFCNT_FROM_PYPY
        keepalive_until_here(w_obj)
    return w_obj


@specialize.ll()
def incref(space, obj):
    make_ref(space, obj)

@specialize.ll()
def decref(space, obj):
    if is_pyobj(obj):
        obj = rffi.cast(PyObject, obj)
        if obj:
            assert obj.c_ob_refcnt > 0
            assert obj.c_ob_pypy_link == 0 or obj.c_ob_refcnt > rawrefcount.REFCNT_FROM_PYPY
            obj.c_ob_refcnt -= 1
            if obj.c_ob_refcnt == 0:
                _Py_Dealloc(space, obj)
    else:
        get_w_obj_and_decref(space, obj)


@cpython_api([PyObject], lltype.Void)
def Py_IncRef(space, obj):
    incref(space, obj)

@cpython_api([PyObject], lltype.Void)
def Py_DecRef(space, obj):
    decref(space, obj)

@cpython_api([PyObject], lltype.Void)
def _Py_NewReference(space, obj):
    obj.c_ob_refcnt = 1
    # XXX is it always useful to create the W_Root object here?
    w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
    assert isinstance(w_type, W_TypeObject)
    get_typedescr(w_type.layout.typedef).realize(space, obj)

@cpython_api([PyObject], lltype.Void)
def _Py_Dealloc(space, obj):
    from pypy.module.cpyext.api import generic_cpy_call
    pto = obj.c_ob_type
    #print >>sys.stderr, "Calling dealloc slot", pto.c_tp_dealloc, "of", obj, \
    #      "'s type which is", rffi.charp2str(pto.c_tp_name)
    rawrefcount.mark_deallocating(w_marker_deallocating, obj)
    generic_cpy_call(space, pto.c_tp_dealloc, obj)

@cpython_api([rffi.VOIDP], lltype.Signed, error=CANNOT_FAIL)
def _Py_HashPointer(space, ptr):
    return rffi.cast(lltype.Signed, ptr)
