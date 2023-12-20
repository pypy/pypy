from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import widen
from rpython.rlib import rgc, jit, rawrefcount
from rpython.rlib.unroll import unrolling_iterable
#
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root, DescrMismatch
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import GetSetProperty
#
from pypy.module.cpyext import pyobject
from pypy.module.cpyext.methodobject import PyMethodDef, PyCFunction
from pypy.module.cpyext.modsupport import convert_method_defs
from pypy.module.cpyext.api import (PyTypeObjectPtr, cts as cpyts,
            generic_cpy_call, Py_TPFLAGS_HEAPTYPE)
from pypy.module.cpyext import structmemberdefs
from pypy.module.cpyext.state import State
from pypy.module.cpyext.typeobject import PyHeapTypeObject
#
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal.interp_descr import W_HPyMemberDescriptor
from pypy.module._hpy_universal.interp_type import W_HPyObject

@API.func("HPy HPy_FromPyObject(HPyContext *ctx, void *obj)", cpyext=True)
def HPy_FromPyObject(space, handles, ctx, obj):
    if not obj:
        return 0  # HPy_NULL
    w_obj = pyobject.from_ref(space, rffi.cast(pyobject.PyObject, obj))
    return handles.new(w_obj)

@API.func("void *HPy_AsPyObject(HPyContext *ctx, HPy h)", cpyext=True)
def HPy_AsPyObject(space, handles, ctx, h):
    if not h:
        return rffi.cast(rffi.VOIDP, 0)
    w_obj = handles.deref(h)
    pyobj = pyobject.make_ref(space, w_obj)
    return rffi.cast(rffi.VOIDP, pyobj)

@API.func("void *HPy_AsStruct_Legacy(HPyContext *ctx, HPy h)")
def HPy_AsStruct_Legacy(space, handles, ctx, h):
    w_obj = handles.deref(h)
    storage = w_obj._hpy_get_raw_storage(space)
    if not storage:
        # print "HPy_AsStruct_Legacy called on handle with no storage, returning cpext object instead"
        pyobj = pyobject.make_ref(space, w_obj)
        return rffi.cast(rffi.VOIDP, pyobj)
    else:
        pyobj = rffi.cast(pyobject.PyObject, storage)
        if pyobj.c_ob_refcnt > 0:
            # maybe called in a c-api-level finalizer after disconnecting the
            # w_obj/pyobj connection, in that case do not incref
            pyobject.incref(space, pyobj)
    return storage


@API.func("void ObjectFreeNOOP(void *)", cpyext=True, is_helper=True)
def ObjectFreeNOOP(space, *args):
    pass

@jit.dont_look_inside
def create_pyobject_from_storage(space, w_obj, w_metatype=None, basicsize=0):
    # Taken from create_ref, but do not allocate
    storage = w_obj._hpy_get_raw_storage(space)
    w_type = space.type(w_obj)
    if pyobject.w_obj_has_pyobj(w_obj):
        raise oefmt(space.w_TypeError,
            "internal error: seeing a PyObject before one was expected")
    # Make sure all the parent pyobjs have been created
    pyobject.as_pyobj(space, w_type)

    typedescr = pyobject.get_typedescr(w_obj.typedef)
    py_obj = rffi.cast(pyobject.PyObject, storage)
    if w_metatype:
        py_obj.c_ob_type = rffi.cast(PyTypeObjectPtr, pyobject.make_ref(space, w_metatype))
        # Adjust the heaptype pointers
        py_heaptype = rffi.cast(PyHeapTypeObject, py_obj)
        pto = py_heaptype.c_ht_type
        pto.c_tp_flags = rffi.cast(rffi.ULONG, Py_TPFLAGS_HEAPTYPE)
        pto.c_tp_as_async = py_heaptype.c_as_async
        pto.c_tp_as_number = py_heaptype.c_as_number
        pto.c_tp_as_sequence = py_heaptype.c_as_sequence
        pto.c_tp_as_mapping = py_heaptype.c_as_mapping
        pto.c_tp_as_buffer = py_heaptype.c_as_buffer
        pto.c_tp_itemsize = 0
    pyobject.track_reference(space, py_obj, w_obj)
    typedescr.attach(space, py_obj, w_obj)
    # py_obj.c_ob_refcnt += 1
    if w_metatype:
        pto = rffi.cast(PyTypeObjectPtr, py_obj)
        pto.c_tp_basicsize = basicsize
        if basicsize:
            # Disable freeing the PyObject memory since it is managed via the storage
            ll_objectfree = ObjectFreeNOOP.get_llhelper(space)
            pto.c_tp_free = ll_objectfree
        else:
            # There will be no HPy storage, just a "regular" cpyext allocation
            # Make sure tp_basicsize is reasonable
            pto.c_tp_basicsize = rffi.sizeof(pyobject.PyObject.TO)
    return py_obj
    

# ~~~ legacy_methods ~~~
# This is used by both modules and types

def attach_legacy_methods(space, pymethods, w_obj, modname, type_name):
    """
    pymethods is passed as a void*, but it is expected to be a PyMethodDef[].
    Wrap its items into the proper cpyext.W_*Function objects, and attach them
    to w_obj (which can be either a module or a type).
    """
    pymethods = cpyts.cast('PyMethodDef*', pymethods)
    dict_w = {}
    if modname:
        # module conversion
        convert_method_defs(space, dict_w, pymethods, None, w_obj, modname, type_name)
    else:
        # type conversion
        convert_method_defs(space, dict_w, pymethods, w_obj, w_obj, modname, type_name)
    for key, w_func in dict_w.items():
        space.setattr(w_obj, space.newtext(key), w_func)

# ~~~ legacy_members ~~~
# This is used only by types

def attach_legacy_members(space, pymembers, w_type, type_name):
    PyMemberDef = cpyts.gettype('PyMemberDef')
    pymembers = rffi.cast(rffi.CArrayPtr(PyMemberDef), pymembers)
    if not pymembers:
        return
    i = 0
    while True:
        pymember = pymembers[i]
        name = pymember.c_name
        if not name:
            break
        i += 1
        name = rffi.constcharp2str(pymember.c_name)
        doc = rffi.constcharp2str(pymember.c_doc) if pymember.c_doc else None
        offset = rffi.cast(lltype.Signed, pymember.c_offset)
        #
        # NOTE: the following works only because the HPy's
        # HPyMember_FieldType.* happen to have the same numeric value as
        # cpyexts' structmemberdefs.T_*
        kind = rffi.cast(lltype.Signed, pymember.c_type)
        #
        # XXX: write tests about the other flags? I think that READ_RESTRICTED
        # and WRITE_RESTRICTED are not used nowadays?
        flags = rffi.cast(lltype.Signed, pymember.c_flags)
        is_readonly = flags & structmemberdefs.READONLY
        w_member = W_HPyMemberDescriptor(w_type, kind, name, doc, offset, is_readonly)
        w_type.setdictvalue(space, name, w_member)

# ~~~ legacy_getset ~~~
# This is used only by types

def check_descr(space, w_self, w_type):
    if not space.isinstance_w(w_self, w_type):
        raise DescrMismatch()

# Copied from cpyext.typeobject, but modified the call to use get_pyobject
class GettersAndSetters:
    def getter(self, space, w_self):
        assert isinstance(self, W_GetSetPropertyHPy)
        assert isinstance(w_self, W_HPyObject)
        check_descr(space, w_self, self.w_type)
        return generic_cpy_call(
            space, self.getset.c_get, w_self.get_pyobject(),
            self.getset.c_closure)

    def setter(self, space, w_self, w_value):
        assert isinstance(self, W_GetSetPropertyHPy)
        assert isinstance(w_self, W_HPyObject)
        assert isinstance(w_value, W_HPyObject)
        check_descr(space, w_self, self.w_type)
        res = generic_cpy_call(
            space, self.getset.c_set,
            w_self.get_pyobject(), w_value.get_pyobject(),
            self.getset.c_closure)
        if rffi.cast(lltype.Signed, res) < 0:
            state = space.fromcache(State)
            state.check_and_raise_exception()

    def deleter(self, space, w_self):
        assert isinstance(self, W_GetSetPropertyHPy)
        assert isinstance(w_self, W_HPyObject)
        check_descr(space, w_self, self.w_type)
        res = generic_cpy_call(
            space, self.getset.c_set, w_self.get_pyobject(), None,
            self.getset.c_closure)
        if rffi.cast(lltype.Signed, res) < 0:
            state = space.fromcache(State)
            state.check_and_raise_exception()

# Copied from cpyext.typeobject, but use the local GettersAndSetters
class W_GetSetPropertyHPy(GetSetProperty):
    def __init__(self, getset, w_type):
        self.getset = getset
        self.w_type = w_type
        doc = fset = fget = fdel = None
        if doc:
            # XXX dead code?
            doc = rffi.constcharp2str(getset.c_doc)
        if getset.c_get:
            fget = GettersAndSetters.getter.im_func
        if getset.c_set:
            fset = GettersAndSetters.setter.im_func
            fdel = GettersAndSetters.deleter.im_func
        GetSetProperty.__init__(self, fget, fset, fdel, doc,
                                cls=None, use_closure=True,
                                tag="HPy_legacy")
        self.name = rffi.constcharp2str(getset.c_name)

    def readonly_attribute(self, space):   # overwritten
        raise oefmt(space.w_AttributeError,
            "attribute '%s' of '%N' objects is not writable",
            self.name, self.w_type)

def attach_legacy_getsets(space, pygetsets, w_type):
    from pypy.module.cpyext.typeobjectdefs import PyGetSetDef
    getsets = rffi.cast(rffi.CArrayPtr(PyGetSetDef), pygetsets)
    if getsets:
        i = -1
        while True:
            i = i + 1
            getset = getsets[i]
            name = getset.c_name
            if not name:
                break
            name = rffi.constcharp2str(name)
            w_descr = W_GetSetPropertyHPy(getset, w_type)
            space.setattr(w_type, space.newtext(name), w_descr)

# ~~~ legacy_slots ~~~
# This is used only by types

def make_slot_wrappers_table():
    from pypy.module.cpyext.typeobject import SLOT_TABLE
    from pypy.module.cpyext.slotdefs import slotdefs
    table = [] # (slotnum, method_name, doc, wrapper_class)
    for typeslot in slotdefs:
        # ignore pypy-specific slots
        if typeslot.slot_names[-1] in ('c_bf_getbuffer',
                                       'c_bf_getreadbuffer',
                                       'c_bf_getwritebuffer'):
            continue
        for num, membername, slotname, TARGET in SLOT_TABLE:
            if typeslot.slot_names[-1] == slotname:
                ts = typeslot
                table.append((num, ts.method_name, ts.doc, ts.wrapper_class))
                break
        else:
            assert False, 'Cannot find slot num for typeslot %s' % typeslot.slot_name
    return table
SLOT_WRAPPERS_TABLE = unrolling_iterable(make_slot_wrappers_table())

@jit.dont_look_inside
def attach_legacy_slots_to_type(space, w_type, c_legacy_slots, needs_hpytype_dealloc):
    from pypy.module.cpyext.slotdefs import wrap_unaryfunc
    from pypy.module.cpyext.typeobjectdefs import newfunc, destructor, allocfunc, freefunc
    slotdefs = rffi.cast(rffi.CArrayPtr(cpyts.gettype('PyType_Slot')), c_legacy_slots)
    i = 0
    type_name = w_type.getqualname(space)
    pytype = rffi.cast(PyTypeObjectPtr, pyobject.as_pyobj(space, w_type))
    while True:
        slotdef = slotdefs[i]
        slotnum = rffi.cast(lltype.Signed, slotdef.c_slot)
        if slotnum == 0:
            break
        elif slotnum == cpyts.macros['Py_tp_methods']:
            attach_legacy_methods(space, slotdef.c_pfunc, w_type, None, type_name)
        elif slotnum == cpyts.macros['Py_tp_members']:
            attach_legacy_members(space, slotdef.c_pfunc, w_type, type_name)
        elif slotnum == cpyts.macros['Py_tp_getset']:
            attach_legacy_getsets(space, slotdef.c_pfunc, w_type)
        elif slotnum == cpyts.macros['Py_tp_dealloc']:
            if needs_hpytype_dealloc:
                raise oefmt(space.w_TypeError,
                    "legacy tp_dealloc is incompatible with HPy_tp_traverse"
                    " or HPy_tp_destroy.")
            # asssign ((PyTypeObject *)w_type)->tp_dealloc
            w_type.has_tp_dealloc = True
            funcptr = slotdef.c_pfunc
            if not hasattr(space, 'is_fake_objspace'):
                # the following lines break test_ztranslation :(
                pytype.c_tp_dealloc = rffi.cast(destructor, funcptr)
    
        elif slotnum == cpyts.macros['Py_tp_new']:
            funcptr = slotdef.c_pfunc
            pytype.c_tp_new = rffi.cast(newfunc, funcptr)
        elif slotnum == cpyts.macros['Py_tp_alloc']:
            funcptr = slotdef.c_pfunc
            pytype.c_tp_alloc = rffi.cast(allocfunc, funcptr)
        elif slotnum == cpyts.macros['Py_tp_free']:
            funcptr = slotdef.c_pfunc
            # XXX this will mess up the no-op free, so maybe
            # raise an error?
            pytype.c_tp_free = rffi.cast(freefunc, funcptr)
        else:
            attach_legacy_slot(space, w_type, slotdef, slotnum, type_name)
        i += 1

def attach_legacy_slot(space, w_type, slotdef, slotnum, type_name):
    
    for num, method_name, doc, wrapper_class in SLOT_WRAPPERS_TABLE:
        if num == slotnum:
            if wrapper_class is None:
                # XXX: we probably need to handle manually these slots
                raise oefmt(space.w_NotImplementedError,
                            "slot wrapper for slot %d %s",num, method_name)
            funcptr = slotdef.c_pfunc
            w_wrapper = wrapper_class(space, w_type, method_name, doc, funcptr, type_name)
            w_type.setdictvalue(space, method_name, w_wrapper)
            break
    else:
        raise oefmt(space.w_NotImplementedError,
            'cannot find the slot %d when creating type %s', slotnum, type_name)
