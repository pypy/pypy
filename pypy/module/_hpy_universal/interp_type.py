from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import rgc
from rpython.rlib import jit
from rpython.rlib.rarithmetic import widen
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib.objectmodel import specialize
from pypy.objspace.std.typeobject import W_TypeObject, find_best_base, _check as check_is_type
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.interpreter.error import oefmt, OperationError
from pypy.interpreter.typedef import interp2app
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.argument import Arguments
from pypy.module.cpyext.pyobject import as_pyobj, PyObject
from pypy.module._hpy_universal.apiset import API, DEBUG
from pypy.module._hpy_universal import llapi
from pypy.module.__builtin__.abstractinst import abstract_issubclass_w
from .interp_slot import (fill_slot, W_wrap_getbuffer, get_slot_cls,
                          W_wrap_call, W_wrap_call_at_offset)
from .interp_descr import add_member, add_getset
from rpython.rlib.rutf8 import surrogate_in_utf8

HPySlot_Slot = llapi.cts.gettype('HPySlot_Slot')
Shapes = llapi.cts.gettype("HPyType_BuiltinShape")


# ========== Implementation of HPy objects ==========
#
# HPy objects are instances of HPy types, defined in C. One pecularity of HPy
# objects is that they need a certain amount of "C memory" which contains the
# user data.
#
# From C, you can access the "C memory" by calling HPy_AsStruct_* on a handle:
# the invariant is that the pointer returned by HPy_AsStruct_* is valid for the
# whole lifetime of the handle, so we need to ensure that the GC doesn't move
# the memory.
#
# The current solution is to use HPY_STORAGE to hold the user data: it is a
# varsized GcStruct wrapping the char array 'data'.  Moreover, HPY_STORAGE is
# allocated using nonmovable=True, because it's the easiest way to ensure that
# the memory never moves. See below for more ideas.
#
# We need a GcStruct instead of a raw-malloc because we want to install a
# custom GC tracer, which calls the user-defined tp_traverse in order to trace
# all the HPyField.
#
# Note that this is suboptimal; currently, an HPy object is represented this
# way:
#
#   1. a W_HPyObject allocated in the nursery, which contains a pointer to (2)
#   2. a HPY_STORAGE allocted as non-movable, which contains a GC header + a
#      word to store the array size + the data itself
#
# So, for each HPy object, we do two allocations and we waste 3 words (one for
# the pointer, one for the HPY_STORAGE GC header, one for HPY_STORAGE array
# size).  This means that there is room for at least two improvments:
#
#   1. RPython support for varsized instances, so that we can inline the user
#      data directly inside W_HPyObject
#
#   2. better support for GC pinning, so that we don't have to allocate the
#      HPY_STORAGE as nonmovable

HPY_STORAGE = lltype.GcStruct(
    'HPyStorage',
    ('tp_traverse', llapi.cts.gettype('HPyFunc_traverseproc')),
    ('data', lltype.Array(lltype.Char)),
)

DATA_OFS = llmemory.offsetof(HPY_STORAGE, 'data')
DATA_ITEM0_OFS = llmemory.itemoffsetof(HPY_STORAGE.data, 0)

# later the JIT should probably be able to look into this, but atm it's too
# difficult
@jit.dont_look_inside
def storage_alloc(size):
    """
    Allocate an HPY_STORAGE containing 'size' bytes of user data. The memory is
    guaranteed to be zeroed.
    """
    # ideally we sould like to use lltype.malloc(..., zero=True), but this is
    # not supported by the GC transformer if it's varsized, see
    # rpython/memory/gctransform/framework.py:gen_zero_gc_pointers
    s = lltype.malloc(HPY_STORAGE, size, nonmovable=True) #, zero=True)
    s.tp_traverse = llapi.cts.cast('HPyFunc_traverseproc', 0) # set by _create_instance
    raw_mem = storage_get_raw_data(s)
    rffi.c_memset(raw_mem, 0, size)  # manually zero the memory
    return s

# we neet @jit.dont_look_inside because of the codewriter, see
# jtransform.py:rewrite_op_cast_ptr_to_adr:
#     cast_ptr_to_adr for GC types unsupported
@jit.dont_look_inside
def storage_get_raw_data(storage):
    base_adr = llmemory.cast_ptr_to_adr(storage)
    data_adr = base_adr + DATA_OFS + DATA_ITEM0_OFS
    raw_mem = rffi.cast(rffi.VOIDP, data_adr)
    return raw_mem

@jit.dont_look_inside
def hpy_customtrace(gc, addr, callback, arg1, arg2):
    storage = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(HPY_STORAGE))
    if storage.tp_traverse:
        trace_one_field = make_trace_one_field(callback)
        ll_trace_one_field = trace_one_field.get_llhelper()
        trace_one_field.gc = gc
        trace_one_field.arg1 = arg1
        trace_one_field.arg2 = arg2
        #
        data_adr = (addr + DATA_OFS + DATA_ITEM0_OFS)
        data_ptr = llmemory.cast_adr_to_ptr(data_adr, rffi.VOIDP)
        NULL = rffi.cast(rffi.VOIDP, 0)
        storage.tp_traverse(data_ptr, ll_trace_one_field, NULL)
hpy_customtrace._skip_collect_analyzer_ = True
#               ^^^
# the GC makes a sanity check to ensure that customtrace functions cannot call
# the GC itself, but here it is confused by the call to tp_traverse, which it
# cannot analyze and thus assumes to have random effects. We know by design
# that tp_traverse cannot invoke the GC (because we don't pass a ctx to it),
# so we just bypass the sanity check. This measn that you need to be extra
# cautions when modifying hpy_customtrace, and double check that you don't
# insert any operation which can actually collect.

@specialize.memo()
def make_trace_one_field(callback):
    """
    Create a ll callback for hpy_customtrace. In particular:

    1. a class TraceOneField_gc_callback_xxx, specialized on the given callback;
    2. a singleton of this class;
    3. an llhelper with the right C signature which fishes the arguments from
       the singleton and calls 'callback'.
    4. the singleton is returned, and you can call .get_llhelper() to get the
       ll callback

    Note that the arguments for the callback (gc, arg1, arg2) are passed by
    setting fields on the singleton. This works because we know that the GC
    does not do concurrent calls to the callback, and it's much easier than
    trying to pack these three arguments into the single void* arg thich
    ll_trace_one_field receives.
    """
    # 1. the class specialized on the callback
    sig = "int ll_trace_one_field(HPyField *f, void *ignored)"
    _, FUNC, _ = API.parse_signature(sig, error_value=API.int(-1))

    class TraceOneField(object):
        @staticmethod
        def get_llhelper():
            return llhelper(FUNC, ll_trace_one_field)
    TraceOneField.__name__ = 'TraceOneField_%s' % callback.__name__

    # 2. the singleton
    trace_one_field = TraceOneField()

    # 3. the llhelper
    def ll_trace_one_field(field_ptr, ignored):
        gc = trace_one_field.gc
        arg1 = trace_one_field.arg1
        arg2 = trace_one_field.arg2
        field_adr = llmemory.cast_ptr_to_adr(field_ptr)
        gc._trace_callback(callback, arg1, arg2, field_adr)
        return API.int(0)

    # 4. return the singleton
    return trace_one_field


def setup_hpy_storage():
    rgc.register_custom_trace_hook(HPY_STORAGE, lambda: hpy_customtrace)

# =====================================================
def check_true(s_arg, bookeeper):
    assert s_arg.const is True


class HPyStorageHolder(W_Root):
    typedef = None
    hpy_storage = lltype.nullptr(HPY_STORAGE)


# =====================================================


class W_HPyObject(W_ObjectObject):
    hpy_storage = lltype.nullptr(HPY_STORAGE)

    # XXX make _hpy_get_raw_storage more efficient for object subclasses

    def get_pyobject(self):
        w_type = self.space.type(self)
        assert isinstance(w_type, W_HPyTypeObject)
        assert w_type.is_legacy()
        storage = self._hpy_get_raw_storage(self.space)
        return rffi.cast(PyObject, storage)

    def _finalize_(self):
        w_type = self.space.type(self)
        assert isinstance(w_type, W_HPyTypeObject)
        storage = self._hpy_get_raw_storage(self.space)
        if w_type.is_cpytype() or w_type.is_legacy():
            # XXX make sure the tp_refcnt is "0"
            pass
        if w_type.tp_finalize:
            from pypy.interpreter.argument import Arguments
            w_type.tp_finalize.call(self.space, Arguments(self.space, [self]))
        # XXX this is still wrong
        if w_type.tp_destroy and storage:
            w_type.tp_destroy(storage)
            self._hpy_set_raw_storage(self.space, lltype.nullptr(HPY_STORAGE))


class W_HPyTypeObject(W_TypeObject):
    hpy_storage = lltype.nullptr(HPY_STORAGE)
    basicsize = 0
    tp_destroy = lltype.nullptr(llapi.cts.gettype('HPyFunc_destroyfunc').TO)
    tp_traverse = lltype.nullptr(llapi.cts.gettype('HPyFunc_traverseproc').TO)
    tp_finalize = None
    # flag to create a pyobj for this w_obj
    has_tp_dealloc = False
    shape = 0


    def get_pyobject(self):
        w_type = self.space.type(self)
        assert isinstance(w_type, W_HPyTypeObject)
        assert w_type.is_legacy()
        storage = self._hpy_get_raw_storage(space)
        return rffi.cast(PyObject, storage)

    def _finalize_(self):
        w_type = self.space.type(self)
        assert isinstance(w_type, W_HPyTypeObject)
        storage = self._hpy_get_raw_storage(self.space)
        if w_type.is_cpytype() or w_type.is_legacy():
            # XXX make sure the tp_refcnt is "0"
            pass
        if w_type.tp_finalize:
            from pypy.interpreter.argument import Arguments
            w_type.tp_finalize.call(self.space, Arguments(self.space, [self]))
        if w_type.tp_destroy and storage:
            w_type.tp_destroy(storage)
            self._hpy_set_raw_storage(self.space, lltype.nullptr(HPY_STORAGE))

    def __init__(self, space, name, bases_w, dict_w, basicsize=0,
                 shape=0):
        # XXX: there is a discussion going on to make it possible to create
        # non-heap types with HPyType_FromSpec. Remember to fix this place
        # when it's the case.
        W_TypeObject.__init__(self, space, name, 
            bases_w, dict_w, is_heaptype=True)
        assert isinstance(self, W_HPyTypeObject)
        self.basicsize = basicsize
        self.shape = shape

    def is_legacy(self):
        return self.shape == Shapes.HPyType_BuiltinShape_Legacy

@API.func("void *HPy_AsStruct_Object(HPyContext *ctx, HPy h)")
def HPy_AsStruct_Object(space, handles, ctx, h):
    w_obj = handles.deref(h)
    storage = w_obj._hpy_get_raw_storage(space)
    return storage

# @API.func("void *HPy_AsStruct_Legacy(HPyContext *ctx, HPy h)")
# def HPy_AsStruct_Legacy(space, handles, ctx, h):
#    see interp_cpy_compat, since this must incref the return value

@API.func("void * HPy_AsStruct_Type(HPyContext *ctx, HPy h)", error_value="CANNOT_FAIL")
def HPy_AsStruct_Type(space, handles, ctx, h):
    from pypy.module.cpyext.typeobject import PyHeapTypeObject
    w_obj = handles.deref(h)
    storage = w_obj._hpy_get_raw_storage(space)
    return storage

@API.func("HPy _HPy_New(HPyContext *ctx, HPy h_type, void **data)")
def _HPy_New(space, handles, ctx, h_type, data):
    w_type = handles.deref(h_type)
    # XXX there must be a better way to figure this out ...
    use__create_instance = False
    try:
        space.w_object.check_user_subclass(w_type)
        use__create_instance = True
    except:
        pass
    if use__create_instance:
        w_result = _create_instance(space, w_type)
    else:
        w_result = _create_instance_subtype(space, w_type, Arguments(space, []))
    data = llapi.cts.cast('void**', data)
    # XXX if the w_type is a cpyext type, make sure the storage is the same as
    # the cpyext one. 
    storage = w_result._hpy_get_raw_storage(space)
    if not storage:
        # print "HPy_New: setting storage for type '%s' to NULL" % space.text_w(space.repr(w_type))
        pass
    data[0] = storage
    h = handles.new(w_result)
    return h


@specialize.arg(0)
def get_bases_and_metaclass_from_params(handles, params):
    KIND = llapi.cts.gettype('HPyType_SpecParam_Kind')
    params = rffi.cast(rffi.CArrayPtr(llapi.cts.gettype('HPyType_SpecParam')), params)
    if not params:
        return [], None
    found_base = False
    found_basestuple = False
    bases_w = []
    w_metaclass = None
    i = 0
    while True:
        # in llapi.py, HPyType_SpecParam.object is declared of type "struct
        # _HPy_s", so we need to manually fish the ._i inside
        p_kind = rffi.cast(lltype.Signed, params[i].c_kind)
        p_h = params[i].c_object.c__i
        if p_kind == 0:
            break
        i += 1
        if p_kind == KIND.HPyType_SpecParam_Base:
            found_base = True
            w_base = handles.deref(p_h)
            bases_w.append(w_base)
        elif p_kind == KIND.HPyType_SpecParam_BasesTuple:
            if found_basestuple:
                raise oefmt(handles.space.w_TypeError,
                    "multiple specifications of HPyType_SpecParam_BasesTuple")
            found_basestuple = True
            w_bases = handles.deref(p_h)
            bases_w = handles.space.unpackiterable(w_bases)
        elif p_kind == KIND.HPyType_SpecParam_Metaclass:
            if w_metaclass:
                raise oefmt(handles.space.w_ValueError,
                    "metaclass was specified multiple times")
            w_metaclass = handles.deref(p_h)
        else:
            raise NotImplementedError('XXX write a test')

    if found_basestuple and found_base:
        raise oefmt(handles.space.w_TypeError,
            "cannot specify both HPyType_SpecParam_Base and "
            "HPytype_SpecParam_BasesTuple")

    # return a copy of bases_w to ensure that it's a not-resizable list
    return make_sure_not_resized(bases_w[:]), w_metaclass

def check_legacy_consistent(space, spec):
    if spec.c_legacy_slots and widen(spec.c_builtin_shape) != Shapes.HPyType_BuiltinShape_Legacy:
        raise oefmt(space.w_TypeError,
            "cannot specify .legacy_slots without setting .builtin_shape"
            "=HPyType_BuiltinShape_Legacy")
    if widen(spec.c_flags) & llapi.HPy_TPFLAGS_INTERNAL_PURE:
        raise oefmt(space.w_TypeError,
                    "HPy_TPFLAGS_INTERNAL_PURE should not be used directly,"
                    " set .legacy=true instead")

def check_inheritance_constraints(space, w_type):
    assert isinstance(w_type, W_HPyTypeObject)
    w_base = find_best_base(w_type.bases_w)
    if (isinstance(w_base, W_HPyTypeObject) and not w_base.is_legacy() and
            w_type.is_legacy()):
        raise oefmt(space.w_TypeError,
            "A legacy type should not inherit its memory layout from a"
            " pure type")

def check_have_gc_and_tp_traverse(space, spec):
    # if we specify HPy_TPFLAGS_HAVE_GC, we must provide a tp_traverse
    have_gc = widen(spec.c_flags) & llapi.HPy_TPFLAGS_HAVE_GC
    if have_gc and not has_tp_slot(spec, [HPySlot_Slot.HPy_tp_traverse]):
        raise oefmt(space.w_ValueError,
                    "You must provide an HPy_tp_traverse slot if you specify "
                    "HPy_TPFLAGS_HAVE_GC")



@API.func("HPy HPyType_FromSpec(HPyContext *ctx, HPyType_Spec *spec, HPyType_SpecParam *params)")
def HPyType_FromSpec(space, handles, ctx, spec, params):
    return _hpytype_fromspec(handles, spec, params)

@DEBUG.func("HPy debug_HPyType_FromSpec(HPyContext *ctx, HPyType_Spec *spec, HPyType_SpecParam *params)", func_name='HPyType_FromSpec')
def debug_HPyType_FromSpec(space, handles, ctx, spec, params):
    return _hpytype_fromspec(handles, spec, params)

@specialize.arg(0)
def _hpytype_fromspec(handles, spec, params):
    """
    """
    # avoid circular import
    from .interp_cpy_compat import attach_legacy_slots_to_type, create_pyobject_from_storage
    space = handles.space
    check_legacy_consistent(space, spec)
    check_have_gc_and_tp_traverse(space, spec)

    dict_w = {}
    specname = rffi.constcharp2str(spec.c_name)
    dotpos = specname.rfind('.')
    if dotpos < 0:
        name = specname
        modname = None
    else:
        name = specname[dotpos + 1:]
        modname = specname[:dotpos]

    if modname is not None:
        dict_w['__module__'] = space.newtext(modname)

    bases_w, w_metaclass = get_bases_and_metaclass_from_params(handles, params)
    shape = widen(spec.c_builtin_shape)
    if shape < Shapes.HPyType_BuiltinShape_Legacy or shape > Shapes.HPyType_BuiltinShape_List:
        raise oefmt(space.w_ValueError, "invalid shape %d", shape)
    is_legacy =  shape == Shapes.HPyType_BuiltinShape_Legacy
    basicsize = rffi.cast(lltype.Signed, spec.c_basicsize)
    if not bases_w:
        # override object.__new__ with one that allocates space for the C
        # struct. It could be further overridden via a tp_new in the spec
        #
        dict_w['__new__'] = get_default_new(space)
    elif  basicsize > 0:
        dict_w['__new__'] = get_default_new_subtype(space)
    else:
        pass

    has_tp_call = False
    if has_tp_slot(spec, [HPySlot_Slot.HPy_tp_call]):
        if widen(spec.c_itemsize):
            # Slot 'HPy_tp_call' will add a hidden field to
            # the type's struct on CPython. The field can only be appended
            # which conflicts with var objects. So, we don't allow this if
            # itemsize != 0. */
            raise oefmt(space.w_TypeError,
                "Cannot use HPy call protocol with var objects")
        has_tp_call = True
    if not w_metaclass:
        w_metaclass = space.w_type

    w_result = _create_new_type(
        space, name, w_metaclass, bases_w, dict_w, basicsize, shape)
    if spec.c_doc:
        w_doc = space.newtext(rffi.constcharp2str(spec.c_doc))
        w_result.setdictvalue(space, '__doc__', w_doc)
    if spec.c_defines:
        add_slot_defs(handles, w_result, spec)
    check_inheritance_constraints(space, w_result)
    if is_legacy:
        create_pyobject_from_storage(space, w_result, w_metatype=w_metaclass,
                                              basicsize=basicsize)
    if spec.c_legacy_slots:
        needs_hpytype_dealloc = has_tp_slot(spec,
                         [HPySlot_Slot.HPy_tp_traverse, HPySlot_Slot.HPy_tp_destroy])
        attach_legacy_slots_to_type(space, w_result, spec.c_legacy_slots, needs_hpytype_dealloc)
    if  has_tp_call and basicsize == 0 and is_legacy:
        # This condition is really only a CPython problem.
        #
        # CPython cannot safely add the hidden field in case of a legacy
        # type that inherits the basicsize since we don't know it.
        # In this case, we reject to use HPy_tp_call but since it
        # is a legacy type, legacy slot Py_tp_call can be used.
        raise oefmt(space.w_TypeError,
            "Cannot use HPy call protocol with legacy types that"
            " inherit the struct. Either set the basicsize to a"
            "non-zero value or use legacy slot 'Py_tp_call'.")
    return handles.new(w_result)

@specialize.arg(0)
def add_slot_defs(handles, w_result, spec):
    from .interp_module import get_doc  # avoid circular import
    space = handles.space
    p = spec.c_defines
    i = 0
    HPyDef_Kind = llapi.cts.gettype('HPyDef_Kind')
    rbp = llapi.cts.cast('HPyFunc_releasebufferproc', 0)
    vectorcalloffset = 0
    has_tp_call = False
    filled_mp_subscript = False
    filled_nb_multiply = False
    filled_nb_add = False
    filled_nb_inplace_multiply = False
    filled_nb_inplace_add = False
    filled_mp_ass_subscript = False
    while p[i]:
        kind = rffi.cast(lltype.Signed, p[i].c_kind)
        if kind == HPyDef_Kind.HPyDef_Kind_Slot:
            hpyslot = llapi.cts.cast('_pypy_HPyDef_as_slot*', p[i]).c_slot
            slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
            if slot_num == HPySlot_Slot.HPy_bf_releasebuffer:
                rbp = llapi.cts.cast('HPyFunc_releasebufferproc',
                                     hpyslot.c_impl)
                i += 1
                continue
            # prefer mp_subscript over sq_item
            elif slot_num == HPySlot_Slot.HPy_sq_item:
                if filled_mp_subscript:
                    i += 1
                    continue
            elif slot_num == HPySlot_Slot.HPy_mp_subscript:
                filled_mp_subscript = True
            # prefer nb_add over sq_concat
            elif slot_num == HPySlot_Slot.HPy_sq_concat:
                if filled_nb_add:
                    i += 1
                    continue
            elif slot_num == HPySlot_Slot.HPy_nb_add:
                filled_nb_add = True
            # prefer nb_multiply over sq_repeat
            elif slot_num == HPySlot_Slot.HPy_sq_repeat:
                if filled_nb_multiply:
                    i += 1
                    continue
            elif slot_num == HPySlot_Slot.HPy_nb_multiply:
                filled_nb_multiply = True
            # prefer nb_inplace_add over sq_inplace_concat
            elif slot_num == HPySlot_Slot.HPy_sq_inplace_concat:
                if filled_nb_inplace_add:
                    i += 1
                    continue
            elif slot_num == HPySlot_Slot.HPy_nb_inplace_add:
                filled_nb_inplace_add = True
            # prefer nb_inplace_multiply over sq_inplace_repeat
            elif slot_num == HPySlot_Slot.HPy_sq_inplace_repeat:
                if filled_nb_inplace_multiply:
                    i += 1
                    continue
            elif slot_num == HPySlot_Slot.HPy_nb_inplace_multiply:
                filled_nb_inplace_multiply = True
            # prefer mp_ass_subscript over sq_ass_item
            elif slot_num == HPySlot_Slot.HPy_sq_ass_item:
                if filled_mp_ass_subscript:
                    i += 1
                    continue
            elif slot_num == HPySlot_Slot.HPy_mp_ass_subscript:
                filled_mp_ass_subscript = True
            #
            has_tp_call = fill_slot(handles, w_result, hpyslot)
        elif kind == HPyDef_Kind.HPyDef_Kind_Meth:
            hpymeth = p[i].c_meth
            name = rffi.constcharp2str(hpymeth.c_name)
            sig = rffi.cast(lltype.Signed, hpymeth.c_signature)
            doc = get_doc(hpymeth.c_doc)
            w_extfunc = handles.w_ExtensionMethod(
                space, handles, name, sig, doc, hpymeth.c_impl, w_result)
            w_result.setdictvalue(
                space, rffi.constcharp2str(hpymeth.c_name), w_extfunc)
        elif kind == HPyDef_Kind.HPyDef_Kind_Member:
            hpymember = llapi.cts.cast('_pypy_HPyDef_as_member*', p[i]).c_member
            old_vectorcalloffset = vectorcalloffset
            vectorcalloffset = add_member(space, w_result, hpymember)
            if old_vectorcalloffset > 0 and vectorcalloffset > 0:
                raise oefmt(space.w_ValueError, "set __vectoroffset__ twice")
        elif kind == HPyDef_Kind.HPyDef_Kind_GetSet:
            hpygetset = llapi.cts.cast('_pypy_HPyDef_as_getset*', p[i]).c_getset
            add_getset(handles, w_result, hpygetset)
        else:
            raise oefmt(space.w_ValueError, "Unspported HPyDef.kind: %d", kind)
        i += 1
    if has_tp_call and vectorcalloffset > 0:
        raise oefmt(space.w_TypeError,
            "Cannot have HPy_tp_call and explicit member"
            "'__vectorcalloffset__'. Specify just one of them.")
    if rbp:
        w_buffer_wrapper = w_result.getdictvalue(space, '__buffer__')
        # XXX: this is horrible :-(
        getbuffer_cls = get_slot_cls(handles, W_wrap_getbuffer)
        if w_buffer_wrapper and isinstance(w_buffer_wrapper, getbuffer_cls):
            w_buffer_wrapper.rbp = rbp
    if vectorcalloffset > 0:
        # Make the type callable with the function at __vectorcalloffset__
        void = llapi.cts.cast('HPyCFunction', 0)
        cls = get_slot_cls(handles, W_wrap_call_at_offset)
        w_slot = cls(HPySlot_Slot.HPy_tp_call, "__call__", void, w_result)
        w_slot.offset = vectorcalloffset
        w_result.setdictvalue(space, "__call__", w_slot)


def has_tp_slot(spec, slots):
    if not spec.c_defines:
        return False
    p = spec.c_defines
    i = 0
    HPyDef_Kind = llapi.cts.gettype('HPyDef_Kind')
    rbp = llapi.cts.cast('HPyFunc_releasebufferproc', 0)
    while p[i]:
        kind = rffi.cast(lltype.Signed, p[i].c_kind)
        if kind == HPyDef_Kind.HPyDef_Kind_Slot:
            hpyslot = llapi.cts.cast('_pypy_HPyDef_as_slot*', p[i]).c_slot
            slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
            if slot_num in slots:
                return True
        i += 1
    return False


def _create_new_type(
        space, name, w_metaclass, bases_w, dict_w, basicsize, shape):
    from pypy.module.cpyext.typeobject import PyHeapTypeObject
    heapobjsize = rffi.sizeof(PyHeapTypeObject.TO)
    pos = surrogate_in_utf8(name)
    if pos >= 0:
        raise oefmt(space.w_ValueError, "can't encode character in position "
                    "%d, surrogates not allowed", pos)
    w_type = space.allocate_instance(W_HPyTypeObject, w_metaclass)
    w_type.space = space
    storagesize = 0
    tp_traverse = lltype.nullptr(llapi.cts.gettype('HPyFunc_traverseproc').TO)
    if isinstance(w_metaclass, W_HPyTypeObject):
        storagesize = w_metaclass.basicsize
        tp_traverse = w_metaclass.tp_traverse
        if shape == Shapes.HPyType_BuiltinShape_Legacy and storagesize < heapobjsize:
            raise oefmt(space.w_ValueError,
                "metaclass %s has basicsize %d which is less than a PyHeapTypeObject (%d)",
                name, w_metaclass.basicsize, heapobjsize)
    elif w_metaclass.is_cpytype():
        # The metaclass is a c-api type, without any HPy
        from pypy.module.cpyext.pyobject import make_ref, cts
        pyobj = make_ref(space, w_metaclass)
        pytype = cts.cast("PyTypeObject*", pyobj)
        if pytype.c_tp_basicsize < heapobjsize:
            raise oefmt(space.w_ValueError,
                "metaclass %s has basicsize %d which is less than a PyHeapTypeObject (%d)",
                name, pytype.c_tp_basicsize, heapobjsize)
        storagesize = pytype.c_tp_basicsize
        storagesize += pytype.c_tp_itemsize
    elif shape == Shapes.HPyType_BuiltinShape_Legacy:
        storagesize = rffi.sizeof(PyHeapTypeObject.TO)
    if storagesize > 0:
        hpy_storage = storage_alloc(storagesize)
        hpy_storage.tp_traverse = tp_traverse
        w_type._hpy_set_raw_storage(space, hpy_storage)
    W_HPyTypeObject.__init__(w_type,
        space, name, bases_w or [space.w_object], dict_w, basicsize, shape)
    w_type.ready()
    return w_type

def _create_instance(space, w_type, __args__=None):
    # XXX make sure there are no __args__
    w_result = space.allocate_instance(W_HPyObject, w_type)
    w_result.space = space
    return _finish_create_instance(space, w_result, w_type)

def _create_instance_subtype(space, w_type, __args__=None):
    w_type = check_is_type(space, w_type)
    w_bestbase = find_best_base(w_type.bases_w)
    if not w_bestbase:
        w_bestbase = space.w_type
    # implementation of W_TypeObect.descr_call
    # w_result = space.call_obj_args(w_bestbase, w_type, __args__)
    w_oldtype, w_olddescr = w_type.lookup_where('__new__')
    w_newtype, w_newdescr = w_bestbase.lookup_where('__new__')
    if space.config.objspace.usemodules.cpyext:
        w_newtype, w_newdescr = w_bestbase.hack_which_new_to_call(
            w_newtype, w_newdescr)
    #
    w_newfunc = space.get(w_newdescr, space.w_None, w_type=w_bestbase)
    w_oldfunc = space.get(w_olddescr, space.w_None, w_type=w_type)
    if w_newfunc == w_oldfunc:
        # prevent recursion
        return _create_instance(space, w_type)
    # Here we switch "self" with "w_type"
    w_result = space.call_obj_args(w_newfunc, w_type, __args__)
    return _finish_create_instance(space, w_result, w_type)

def _finish_create_instance(space, w_result, w_type):
    # avoid circular import
    from pypy.module._hpy_universal.interp_cpy_compat import create_pyobject_from_storage
    from pypy.module.cpyext.pyobject import make_ref, cts
    if isinstance(w_type, W_HPyTypeObject):
        w_hpybase = w_type
    else:
        # a subclass?
        assert isinstance(w_type, W_TypeObject)
        w_hpybase = w_type
        for w_b in w_type.mro_w:
            if isinstance(w_b, W_HPyTypeObject):
                w_hpybase = w_b
                break
        else:
            # This can happen via a direct call to HPy_New of a non-hpy type
            return w_result
    assert isinstance(w_hpybase, W_HPyTypeObject)
    if w_hpybase.basicsize > 0:
        if w_result._hpy_get_raw_storage(space):
            # print "already allocated storage"
            pass
        else:
            hpy_storage = storage_alloc(w_hpybase.basicsize)
            hpy_storage.tp_traverse = w_hpybase.tp_traverse
            w_result._hpy_set_raw_storage(space, hpy_storage)
            if w_hpybase.is_cpytype() or w_hpybase.is_legacy():
                pyobj = create_pyobject_from_storage(space, w_result)
                pyobj.c_ob_type = cts.cast("PyTypeObject *", make_ref(space, w_hpybase))
    elif w_hpybase.is_cpytype() or w_hpybase.is_legacy():
        # raise oefmt(space.w_RuntimeError, "see issue 459")
        pass
    if w_hpybase.tp_destroy or w_hpybase.tp_finalize:
        w_result.register_finalizer(space)
    return w_result

descr_new = interp2app(_create_instance)
descr_new_subtype = interp2app(_create_instance_subtype)

@specialize.memo()
def get_default_new(space):
    return descr_new.get_function(space)

@specialize.memo()
def get_default_new_subtype(space):
    return descr_new_subtype.get_function(space)

@API.func("HPy HPyType_GenericNew(HPyContext *ctx, HPy type, HPy *args, HPy_ssize_t nargs, HPy kw)")
def HPyType_GenericNew(space, handles, ctx, h_type, args, nargs, kw):
    w_type = handles.deref(h_type)
    # XXX create an Argument and call space.call()
    w_result = _create_instance(space, w_type)
    return handles.new(w_result)

@API.func("char * HPyType_GetName(HPyContext *ctx, HPy type)")
def HPyType_GetName(space, handles, ctx, h_type):
    w_obj = handles.deref(h_type)
    if isinstance(w_obj, W_TypeObject):
        s = w_obj.name
        return handles.str2ownedptr(s, owner=h_type)
    return handles.str2ownedptr("<unknown>", owner=h_type)

@API.func("long HPyType_GetBuiltinShape(HPyContext *ctx, HPy type)", error_value="CANNOT_FAIL")
def HPyType_GetBuiltinShape(space, handles, ctx, h_type):
    w_obj = handles.deref(h_type)
    if w_obj.is_cpytype():
        return rffi.cast(rffi.LONG, -1) # HPyTYpe_BuiltinShape_Legacy
    if isinstance(w_obj, W_HPyTypeObject):
        return rffi.cast(rffi.LONG, w_obj.shape)
    # XXX FIXME
    return rffi.cast(rffi.LONG, 0)

@API.func("int HPy_SetCallFunction(HPyContext *ctx, HPy h, HPyCallFunction *func)", error_value=API.int(-1))
def HPy_SetCallFunction(space, handles, ctx, h, func):
    w_obj = handles.deref(h)
    # Unconditionally override the __call__ slot on the object
    w_type = space.type(w_obj)
    cls = get_slot_cls(handles, W_wrap_call)
    cfuncptr = llapi.cts.cast('HPyCFunction', func.c_impl)
    w_slot = cls(HPySlot_Slot.HPy_tp_call, "__call__", cfuncptr, w_type)
    w_type.setdictvalue(space, "__call__", w_slot)
    return API.int(0)

@API.func("int HPyType_IsSubtype(HPyContext *ctx, HPy sub, HPy type)", error_value="CANNOT_FAIL")
def HPyType_IsSubtype(space, handles, ctx, sub, typ):
    w_sub = handles.deref(sub)
    w_type = handles.deref(typ)
    return API.int(abstract_issubclass_w(space, w_sub, w_type))
    

