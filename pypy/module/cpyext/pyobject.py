import sys

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root, SpaceCache
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.extregistry import ExtRegistryEntry
from pypy.module.cpyext.api import (
    cpython_api, bootstrap_function, PyObject, PyObjectP, ADDR,
    CANNOT_FAIL, Py_TPFLAGS_HEAPTYPE, PyTypeObjectPtr, is_PyObject,
    PyVarObject, Py_ssize_t, init_function, cts)
from pypy.module.cpyext.state import State
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.boolobject import W_BoolObject
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.mapdict import DevolvedDictTerminator
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_base_ptr
from rpython.rlib import rawrefcount, jit
from rpython.rlib.rawrefcount import _Py_IMMORTAL_REFCNT, refcnt_is_immortal
from rpython.rlib.debug import ll_assert, fatalerror, check_annotation

#________________________________________________________
# ob_pypy_link prefix
#
# ob_pypy_link (the word mapping a C PyObject back to its RPython object) is kept
# in a hidden prefix immediately before the visible PyObject header, so that header
# matches CPython's {ob_refcnt, ob_type} layout for abi3 (Py_TYPE/Py_SIZE inline the
# offsets even under the limited API).  This is the same idea as PyGC_HEAD in CPython.
# The prefix is reserved by every PyObject allocation and reached only through the
# helpers below; the translated GC mirrors this in incminimark.PYOBJ_HDR / _pyobj,
# and the untranslated path in rpython.rlib.rawrefcount.  These helpers may be
# refactored into a small class later.

PYOBJ_LINK_OFFSET = rffi.sizeof(lltype.Signed)   # bytes back from ob_refcnt to ob_pypy_link
PYOBJ_LINK_PREFIX = 16   # padded to 16 so ob_refcnt keeps malloc's 16-byte alignment

# The hidden prefix word, reached by shifting the visible PyObject pointer back.
# ob_refcnt is read straight off the real PyObject, so only the link lives here.
PYOBJ_LINK_HDR = lltype.Struct('PyObjLinkHdr', ('ob_pypy_link', lltype.Signed))
PYOBJ_LINK_HDR_PTR = lltype.Ptr(PYOBJ_LINK_HDR)

def _pyobj_link_hdr(pyobj):
    base = rffi.ptradd(rffi.cast(rffi.CCHARP, pyobj), -PYOBJ_LINK_OFFSET)
    return rffi.cast(PYOBJ_LINK_HDR_PTR, base)

def pyobj_get_link(pyobj):
    return _pyobj_link_hdr(pyobj).ob_pypy_link

def pyobj_set_link(pyobj, value):
    _pyobj_link_hdr(pyobj).ob_pypy_link = value

@specialize.argtype(0)
def pyobj_raw_alloc(size, immortal=False):
    """Raw-allocate a PyObject of 'size' bytes plus the hidden link prefix.
    Returns the visible PyObject pointer (just past the zeroed prefix).  Uses address
    arithmetic (not ptradd) so the untranslated ll2ctypes address->object cache maps
    the base back to the original malloc on free."""
    buf = lltype.malloc(rffi.VOIDP.TO, size + PYOBJ_LINK_PREFIX,
                        flavor='raw', zero=True,
                        add_memory_pressure=True, immortal=immortal)
    res = rffi.cast(rffi.VOIDP, rffi.cast(lltype.Signed, buf) + PYOBJ_LINK_PREFIX)
    return res

def pyobj_raw_free(pyobj):
    base = rffi.cast(rffi.VOIDP, rffi.cast(lltype.Signed, pyobj) - PYOBJ_LINK_PREFIX)
    lltype.free(base, flavor='raw')


#________________________________________________________
# type description

class W_BaseCPyObject(W_ObjectObject):
    """ A subclass of W_ObjectObject that has one field for directly storing
    the link from the w_obj to the cpy ref. This is only used for C-defined
    types. """


def check_true(s_arg, bookeeper):
    assert s_arg.const is True

def w_root_as_pyobj(w_obj, space):
    # make sure that translation crashes if we see this while translating
    # without cpyext
    check_annotation(space.config.objspace.usemodules.cpyext, check_true)
    # immortal static objects are mapped out-of-band (they have no ob_pypy_link)
    py_obj = space.fromcache(State).static_w2py.get(
        w_obj, lltype.nullptr(PyObject.TO))
    if py_obj:
        return py_obj
    # default implementation of _cpyext_as_pyobj
    return rawrefcount.from_obj(PyObject, w_obj)

def w_root_attach_pyobj(w_obj, space, py_obj):
    check_annotation(space.config.objspace.usemodules.cpyext, check_true)
    assert space.config.objspace.usemodules.cpyext
    # default implementation of _cpyext_attach_pyobj
    rawrefcount.create_link_pypy(w_obj, py_obj)

def w_root_attach_pyobj_static(w_obj, space, py_obj):
    # default implementation of _cpyext_attach_pyobj_static: forward mapping for an
    # immortal static object, with NO rawrefcount link (it has no ob_pypy_link prefix).
    # Direct-storage types (W_BaseCPyObject, W_TypeObject) override this to use _cpy_ref.
    space.fromcache(State).static_w2py[w_obj] = py_obj

def track_static_reference(space, py_obj, w_obj):
    """Register an immortal static object (one of pypy_static_pyobjs[]).  Creates NO
    rawrefcount link -- the object is bare, with no ob_pypy_link prefix.  Marks it
    immortal (_Py_IMMORTAL_REFCNT, no REFCNT_FROM_PYPY tag since there is no prefix),
    records the forward mapping through the object's native storage (_cpy_ref for
    direct-storage types, else State.static_w2py via _cpyext_attach_pyobj_static) and
    the reverse mapping in State.static_py2w (consulted by from_ref)."""
    py_obj.c_ob_refcnt = _Py_IMMORTAL_REFCNT
    w_obj._cpyext_attach_pyobj_static(space, py_obj)
    space.fromcache(State).static_py2w[rffi.cast(lltype.Signed, py_obj)] = w_obj


def add_direct_pyobj_storage(cls):
    """ Add the necessary methods to a class to store a reference to the py_obj
    on its instances directly. """

    cls._cpy_ref = lltype.nullptr(PyObject.TO)

    def _cpyext_as_pyobj(self, space):
        return self._cpy_ref
    cls._cpyext_as_pyobj = _cpyext_as_pyobj

    def _cpyext_attach_pyobj(self, space, py_obj):
        self._cpy_ref = py_obj
        rawrefcount.create_link_pypy(self, py_obj)
    cls._cpyext_attach_pyobj = _cpyext_attach_pyobj

    def _cpyext_attach_pyobj_static(self, space, py_obj):
        # immortal static object: forward mapping only, no rawrefcount link
        self._cpy_ref = py_obj
    cls._cpyext_attach_pyobj_static = _cpyext_attach_pyobj_static

add_direct_pyobj_storage(W_BaseCPyObject) 
add_direct_pyobj_storage(W_TypeObject)
add_direct_pyobj_storage(W_NoneObject)
add_direct_pyobj_storage(W_BoolObject)


class BaseCpyTypedescr(object):
    basestruct = PyObject.TO
    W_BaseObject = W_ObjectObject

    def get_dealloc(self, space):
        state = space.fromcache(State)
        return state.C._PyPy_subtype_dealloc

    # CCC port to C
    def allocate(self, space, w_type, itemcount=0, immortal=False, itemsize=-1):
        # typically called from PyType_GenericAlloc via typedescr.allocate
        # this returns a PyObject with ob_refcnt == 1.

        pytype = as_pyobj(space, w_type)
        pytype = rffi.cast(PyTypeObjectPtr, pytype)
        assert pytype
        # Don't increase refcount for non-heaptypes
        flags = rffi.cast(lltype.Signed, pytype.c_tp_flags)
        if flags & Py_TPFLAGS_HEAPTYPE:
            incref(space, pytype)

        size = pytype.c_tp_basicsize
        if itemsize < 0:
            itemsize = pytype.c_tp_itemsize
        if itemsize:
            size += itemcount * itemsize
        assert size >= rffi.sizeof(PyObject.TO)
        buf = pyobj_raw_alloc(size, immortal=immortal)
        pyobj = rffi.cast(PyObject, buf)
        if itemsize or space.issubtype_w(w_type, space.w_list):
            pyvarobj = rffi.cast(PyVarObject, pyobj)
            pyvarobj.c_ob_size = itemcount
        # Mark the existence of the prefix field
        pyobj.c_ob_refcnt = rawrefcount.REFCNT_FROM_PYPY + 1
        pyobj.c_ob_type = pytype
        return pyobj

    def attach(self, space, pyobj, w_obj, w_userdata=None):
        pass

    def realize(self, space, obj):
        w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
        assert isinstance(w_type, W_TypeObject)
        try:
            if w_type.flag_cpytype:
                w_obj = space.allocate_instance(W_BaseCPyObject, w_type)
            else:
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
    assert not isinstance(tp_basestruct, lltype.Ptr), "should pass .TO"

    class CpyTypedescr(BaseCpyTypedescr):
        basestruct = tp_basestruct

        if tp_alloc:
            def allocate(self, space, w_type, itemcount=0, immortal=False, itemsize=-1):
                return tp_alloc(self, space, w_type, itemcount)

        if hasattr(tp_dealloc, 'api_func'):
            def get_dealloc(self, space):
                return tp_dealloc.api_func.get_llhelper(space)
        elif tp_dealloc:
            def get_dealloc(self, space):
                return tp_dealloc

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
    # typedescr for the 'object' type
    state = space.fromcache(State)
    make_typedescr(space.w_object.layout.typedef,
                   dealloc=state.C._PyPy_object_dealloc)
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

@jit.dont_look_inside
def create_ref(space, w_obj, w_userdata=None, immortal=False):
    """
    Allocates a PyObject, and fills its fields with info from the given
    interpreter object.
    """
    w_type = space.type(w_obj)
    pytype = rffi.cast(PyTypeObjectPtr, as_pyobj(space, w_type))
    typedescr = get_typedescr(w_obj.typedef)
    if space.is_w(w_type, space.w_text):
        # These PyUnicodeObjects will always take the compact form
        # since they come from uint8-encoded strings, so we must
        # override the default tp_itemsize (see also unicode_alloc)
        # Maybe this snippet should use the ptype.tp_alloc to allocate the py_obj?
        itemsize = 1
    elif space.is_w(w_type, space.w_type):
        # Subclasses of "type" (which has space for PyMemberDef) do not
        # need space for tp_member like heap types do
        itemsize = 0
    else:
        itemsize = pytype.c_tp_itemsize
    if itemsize != 0 or space.issubtype_w(w_type, space.w_list):
        # PyBytesObject, compact PyUnicodeObject and subclasses
        try:
            # Can cause infinite recursion if w_obj.__len__ is a c function
            # so the call will try to convert w_obj to a pyobj via create_ref
            from pypy.objspace.std.listobject import W_ListObject
            if  isinstance(w_obj, W_ListObject):
                itemcount = w_obj.length()
            else:
                itemcount = space.len_w(w_obj)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                # issue 4013: is this correct?
                itemcount = 0
                # raise oefmt(space.w_SystemError,
                #            "cpyext: Failure to allocate '%N' (with a non-zero "
                #            "tp_itemsize) when len(obj) cannot be calculated",
                #            w_type)
            else:
                raise
    else:
        itemcount = 0
    py_obj = typedescr.allocate(space, w_type, itemcount=itemcount, immortal=immortal)
    track_reference(space, py_obj, w_obj)
    assert py_obj.c_ob_refcnt > rawrefcount.REFCNT_FROM_PYPY
    py_obj.c_ob_refcnt -= 1
    typedescr.attach(space, py_obj, w_obj, w_userdata)
    return py_obj


class CPyExtDictTerminator(DevolvedDictTerminator):
    """Per-class terminator for cpyext types with a nonzero tp_dictoffset
    (see W_PyCTypeObject.get_terminator in cpyext/typeobject.py, overriding
    W_TypeObject.get_terminator). Subclasses DevolvedDictTerminator so every
    dict-kind attribute access already routes through obj.getdict() -- there
    is no per-object unboxed fast path, because the C struct field must stay
    authoritative. dictoffset is fixed per w_cls (basicsize doesn't vary per
    instance), so it's computed once by the caller instead of re-read here.
    """
    def __init__(self, space, w_cls, dictoffset):
        DevolvedDictTerminator.__init__(self, space, w_cls)
        self.dictoffset = dictoffset

    def build_dict(self, obj, space):
        # Called once per object (mapdict caches the result), so this is not
        # a hot path -- no need for a live/re-checking strategy here. Either
        # adopt whatever's already published at the struct field, or create
        # and publish a plain dict, mirroring PyObject_GenericGetDict's
        # get-or-create semantics. Either way there's exactly one dict
        # object for the lifetime of the instance: the struct field and
        # obj.getdict() always agree because they name the same object,
        # not because anything re-checks them against each other.
        py_obj = as_pyobj(space, obj)
        loc = rffi.ptradd(cts.cast("char *", py_obj), self.dictoffset)
        dictptr = cts.cast("PyObject **", loc)
        pyobj = dictptr[0]
        if pyobj:
            result = from_ref(space, pyobj)
        else:
            result = space.newdict()
            dictptr[0] = make_ref(space, result)
        assert isinstance(result, W_DictMultiObject)
        return result


def track_reference(space, py_obj, w_obj):
    """
    Ties py_obj's prefix (marked by refcnt >= REFCNT_FROM_PYPY) to w_obj.
    A foreign py_obj (below the tag, no prefix) is left unlinked.
    """
    # XXX looks like a PyObject_GC_TRACK
    if py_obj.c_ob_refcnt >= rawrefcount.REFCNT_FROM_PYPY:
        w_obj._cpyext_attach_pyobj(space, py_obj)


w_marker_deallocating = W_Root()

@jit.dont_look_inside
def from_ref(space, ref):
    """
    Finds the interpreter object corresponding to the given reference.  If the
    object is not yet realized (see bytesobject.py), creates it.
    """
    assert is_pyobj(ref)
    if not ref:
        return None
    ref = rffi.cast(PyObject, ref)
    if refcnt_is_immortal(ref.c_ob_refcnt):
        if ref.c_ob_refcnt < rawrefcount.REFCNT_FROM_PYPY:
            # prefix-less immortal (bare static): mapped out-of-band.  A miss
            # means an immortal object we did not create (e.g. immortalized by
            # an extension): fall through and realize it like a foreign object.
            w_obj = space.fromcache(State).static_py2w.get(
                rffi.cast(lltype.Signed, ref), None)
            if w_obj is not None:
                return w_obj
        # else: owned immortal, found through its prefix link below
    if ref.c_ob_refcnt >= rawrefcount.REFCNT_FROM_PYPY:
        w_obj = rawrefcount.to_obj(W_Root, ref)
        if w_obj is not None:
            if w_obj is not w_marker_deallocating:
                return w_obj
            type_name = rffi.charp2str(cts.cast('char*', ref.c_ob_type.c_tp_name))
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
                "the CPython extension.\n"
                ">>> This object is of type '%s'" % (type_name,))

    # A foreign object (refcnt below the tag, no prefix) or a not-yet-realized one.
    # Realize it.
    ref_type = rffi.cast(PyObject, ref.c_ob_type)
    if ref_type == ref: # recursion!
        raise InvalidPointerException(str(ref))
    w_type = from_ref(space, ref_type)
    assert isinstance(w_type, W_TypeObject)
    return get_typedescr(w_type.layout.typedef).realize(space, ref)

@jit.dont_look_inside
def as_pyobj(space, w_obj, w_userdata=None, immortal=False):
    """
    Returns a 'PyObject *' representing the given interpreter object.
    This doesn't give a new reference, but the returned 'PyObject *'
    is valid at least as long as 'w_obj' is.  **To be safe, you should
    use keepalive_until_here(w_obj) some time later.**  In case of
    doubt, use the safer make_ref().
    """
    assert not is_pyobj(w_obj)
    if w_obj is not None:
        py_obj = w_obj._cpyext_as_pyobj(space)
        if not py_obj:
            py_obj = create_ref(space, w_obj, w_userdata, immortal=immortal)
        #
        # Try to crash here, instead of randomly, if we don't keep w_obj alive
        # (immortals are prefix-less statics with refcnt pinned below the tag)
        ll_assert(py_obj.c_ob_refcnt >= rawrefcount.REFCNT_FROM_PYPY or
                  refcnt_is_immortal(py_obj.c_ob_refcnt),
                  "Bug in cpyext: The W_Root object was garbage-collected "
                  "while being converted to PyObject.")
        return py_obj
    else:
        return lltype.nullptr(PyObject.TO)
as_pyobj._always_inline_ = 'try'

def pyobj_has_w_obj(pyobj):
    w_obj = rawrefcount.to_obj(W_Root, pyobj)
    return w_obj is not None and w_obj is not w_marker_deallocating

def w_obj_has_pyobj(w_obj):
    return bool(rawrefcount.from_obj(PyObject, w_obj))

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

def get_pyobj_and_incref(space, w_obj, w_userdata=None, immortal=False):
    pyobj = as_pyobj(space, w_obj, w_userdata, immortal=immortal)
    if pyobj:  # != NULL
        if not refcnt_is_immortal(pyobj.c_ob_refcnt):
            assert pyobj.c_ob_refcnt >= rawrefcount.REFCNT_FROM_PYPY
            pyobj.c_ob_refcnt += 1
        keepalive_until_here(w_obj)
    return pyobj

def hack_for_result_often_existing_obj(space, w_obj):
    # Equivalent to get_pyobj_and_incref() and not to make_ref():
    # it builds a PyObject from a W_Root, but ensures that the result
    # gets attached to the original W_Root.  This is needed to work around
    # some obscure abuses: https://github.com/numpy/numpy/issues/9850
    return get_pyobj_and_incref(space, w_obj)

def make_ref(space, w_obj, w_userdata=None, immortal=False):
    """Turn the W_Root into a corresponding PyObject.  You should
    decref the returned PyObject later.  Note that it is often the
    case, but not guaranteed, that make_ref() returns always the
    same PyObject for the same W_Root; for example, integers.
    """
    assert not is_pyobj(w_obj)
    if False and w_obj is not None and space.type(w_obj) is space.w_int:
        # XXX: adapt for pypy3
        state = space.fromcache(State)
        intval = space.int_w(w_obj)
        return state.ccall("PyLong_FromLong", intval)
    return get_pyobj_and_incref(space, w_obj, w_userdata, immortal=False)

@specialize.ll()
def get_w_obj_and_decref(space, pyobj):
    """Decrement the reference counter of the PyObject and return the
    corresponding W_Root object (so the reference count after the decref
    is at least REFCNT_FROM_PYPY and cannot be zero).
    """
    assert is_pyobj(pyobj)
    pyobj = rffi.cast(PyObject, pyobj)
    w_obj = from_ref(space, pyobj)
    if pyobj:
        if refcnt_is_immortal(pyobj.c_ob_refcnt):
            return w_obj   # immortal: refcnt pinned
        pyobj.c_ob_refcnt -= 1
        if pyobj.c_ob_refcnt == 0:
            from pypy.module.cpyext.api import generic_cpy_call
            generic_cpy_call(space, space.fromcache(State).C._Py_Dealloc, pyobj)
        else:
            assert pyobj.c_ob_refcnt >= rawrefcount.REFCNT_FROM_PYPY
        keepalive_until_here(w_obj)
    return w_obj


@specialize.ll()
def incref(space, pyobj):
    assert is_pyobj(pyobj)
    pyobj = rffi.cast(PyObject, pyobj)
    assert pyobj.c_ob_refcnt >= 1
    if refcnt_is_immortal(pyobj.c_ob_refcnt):
        return   # immortal: refcnt pinned, never freed
    pyobj.c_ob_refcnt += 1

@specialize.ll()
def decref(space, pyobj):
    from pypy.module.cpyext.api import generic_cpy_call
    assert is_pyobj(pyobj)
    pyobj = rffi.cast(PyObject, pyobj)
    if pyobj:
        if refcnt_is_immortal(pyobj.c_ob_refcnt):
            return   # immortal: refcnt pinned, never freed
        assert pyobj.c_ob_refcnt > 0
        pyobj.c_ob_refcnt -= 1
        rc = pyobj.c_ob_refcnt
        if rc == 0 or (rc == rawrefcount.REFCNT_FROM_PYPY and pyobj_get_link(pyobj) == 0):
            state = space.fromcache(State)
            generic_cpy_call(space, state.C._Py_Dealloc, pyobj)


@init_function
def write_w_marker_deallocating(space):
    if we_are_translated():
        llptr = cast_instance_to_base_ptr(w_marker_deallocating)
        state = space.fromcache(State)
        state.C.set_marker(llptr)

@cpython_api([rffi.VOIDP], lltype.Signed, error=CANNOT_FAIL)
def _Py_HashPointer(space, ptr):
    return rffi.cast(lltype.Signed, ptr)

@cpython_api([PyObject], lltype.Void)
def Py_IncRef(space, obj):
    if obj:
        incref(space, obj)

@cpython_api([PyObject], lltype.Void)
def Py_DecRef(space, obj):
    decref(space, obj)
