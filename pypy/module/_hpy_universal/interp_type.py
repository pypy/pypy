from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import rgc
from rpython.rlib import jit
from rpython.rlib.rarithmetic import widen
from rpython.rlib.debug import make_sure_not_resized, debug_print
from rpython.rlib.objectmodel import specialize
from pypy.objspace.std.typeobject import W_TypeObject, find_best_base
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.interpreter.error import oefmt
from pypy.interpreter.typedef import interp2app
from pypy.module.cpyext.pyobject import as_pyobj, PyObject
from pypy.module._hpy_universal.apiset import API, DEBUG
from pypy.module._hpy_universal import llapi
from .interp_slot import fill_slot, W_wrap_getbuffer, get_slot_cls
from .interp_descr import add_member, add_getset
from rpython.rlib.rutf8 import surrogate_in_utf8

HPySlot_Slot = llapi.cts.gettype('HPySlot_Slot')


# ========== Implementation of HPy objects ==========
#
# HPy objects are instances of HPy types, defined in C. One pecularity of HPy
# objects is that they need a certain amount of "C memory" which contains the
# user data.
#
# From C, you can access the "C memory" by calling HPy_AsStruct on a handle:
# the invariant is that the pointer returned by HPy_AsStruct is valid for the
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

def hpy_customtrace(gc, adr, callback, arg1, arg2):
    storage = llmemory.cast_adr_to_ptr(adr, lltype.Ptr(HPY_STORAGE))
    if storage.tp_traverse:
        trace_one_field = make_trace_one_field(callback)
        ll_trace_one_field = trace_one_field.get_llhelper()
        trace_one_field.gc = gc
        trace_one_field.arg1 = arg1
        trace_one_field.arg2 = arg2
        #
        data_adr = (adr + DATA_OFS + DATA_ITEM0_OFS)
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


class W_HPyObject(W_ObjectObject):
    hpy_storage = lltype.nullptr(HPY_STORAGE)

    def get_raw_data(self):
        return storage_get_raw_data(self.hpy_storage)

    def get_pyobject(self):
        storage = self.get_raw_data()
        w_type = self.space.type(self)
        assert isinstance(w_type, W_HPyTypeObject)
        assert w_type.is_legacy
        return rffi.cast(PyObject, self.get_raw_data()) 

    def _finalize_(self):
        w_type = self.space.type(self)
        assert isinstance(w_type, W_HPyTypeObject)
        if w_type.tp_finalize:
            from pypy.interpreter.argument import Arguments
            w_type.tp_finalize.call(self.space, Arguments(self.space, [self]))
        if w_type.tp_destroy:
            w_type.tp_destroy(self.get_raw_data())


class W_HPyTypeObject(W_TypeObject):
    basicsize = 0
    tp_destroy = lltype.nullptr(llapi.cts.gettype('HPyFunc_destroyfunc').TO)
    tp_traverse = lltype.nullptr(llapi.cts.gettype('HPyFunc_traverseproc').TO)
    tp_finalize = None
    # flag to create a pyobj for this w_obj
    has_tp_dealloc = False

    def __init__(self, space, name, bases_w, dict_w, basicsize=0,
                 is_legacy=False):
        # XXX: there is a discussion going on to make it possible to create
        # non-heap types with HPyType_FromSpec. Remember to fix this place
        # when it's the case.
        W_TypeObject.__init__(self, space, name, bases_w, dict_w, is_heaptype=True)
        self.basicsize = basicsize
        self.is_legacy = is_legacy


@API.func("void *HPy_AsStruct(HPyContext *ctx, HPy h)")
def HPy_AsStruct(space, handles, ctx, h):
    w_obj = handles.deref(h)
    if not isinstance(w_obj, W_HPyObject):
        # XXX: write a test for this
        raise oefmt(space.w_TypeError, "Object of type '%T' is not a valid HPy object.", w_obj)
    return w_obj.get_raw_data()

@API.func("void *HPy_AsStructLegacy(HPyContext *ctx, HPy h)")
def HPy_AsStructLegacy(space, handles, ctx, h):
    w_obj = handles.deref(h)
    if not isinstance(w_obj, W_HPyObject):
        # XXX: write a test for this
        raise oefmt(space.w_TypeError, "Object of type '%T' is not a valid HPy object.", w_obj)
    return w_obj.get_raw_data()

@API.func("HPy _HPy_New(HPyContext *ctx, HPy h_type, void **data)")
def _HPy_New(space, handles, ctx, h_type, data):
    w_type = handles.deref(h_type)
    w_result = _create_instance(space, w_type)
    data = llapi.cts.cast('void**', data)
    data[0] = w_result.get_raw_data()
    h = handles.new(w_result)
    return h


@specialize.arg(0)
def get_bases_from_params(handles, params):
    KIND = llapi.cts.gettype('HPyType_SpecParam_Kind')
    params = rffi.cast(rffi.CArrayPtr(llapi.cts.gettype('HPyType_SpecParam')), params)
    if not params:
        return []
    found_base = False
    found_basestuple = False
    bases_w = []
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
            found_basestuple = True
            w_bases = handles.deref(p_h)
            bases_w = handles.space.unpackiterable(w_bases)
        else:
            raise NotImplementedError('XXX write a test')

    if found_basestuple > 1:
        raise NotImplementedError('XXX write a test')
    if found_basestuple and found_base:
        raise NotImplementedError('XXX write a test')

    # return a copy of bases_w to ensure that it's a not-resizable list
    return make_sure_not_resized(bases_w[:])

def check_legacy_consistent(space, spec):
    if spec.c_legacy_slots and not widen(spec.c_legacy):
        raise oefmt(space.w_TypeError,
                    "cannot specify .legacy_slots without setting .legacy=true")
    if widen(spec.c_flags) & llapi.HPy_TPFLAGS_INTERNAL_PURE:
        raise oefmt(space.w_TypeError,
                    "HPy_TPFLAGS_INTERNAL_PURE should not be used directly,"
                    " set .legacy=true instead")

def check_inheritance_constraints(space, w_type):
    assert isinstance(w_type, W_HPyTypeObject)
    w_base = find_best_base(w_type.bases_w)
    if (isinstance(w_base, W_HPyTypeObject) and not w_base.is_legacy and
            w_type.is_legacy):
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
    from .interp_cpy_compat import attach_legacy_slots_to_type  # avoid circular import
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

    bases_w = get_bases_from_params(handles, params)
    is_legacy = bool(widen(spec.c_legacy))
    if not bases_w:
        # override object.__new__ with one that allocates space for the C
        # struct. It could be further overridden via a tp_new in the spec
        #
        # For now assume that inheriting from builtin types will never require
        # add C-level fields, only methods, so HPy_AsStruct will never be called
        # on such an instance.
        dict_w['__new__'] = get_default_new(space)
    basicsize = rffi.cast(lltype.Signed, spec.c_basicsize)

    w_result = _create_new_type(
        space, space.w_type, name, bases_w, dict_w, basicsize, is_legacy=is_legacy)
    if spec.c_doc:
        w_doc = space.newtext(rffi.constcharp2str(spec.c_doc))
        w_result.setdictvalue(space, '__doc__', w_doc)
    if spec.c_legacy_slots:
        needs_hpytype_dealloc = has_tp_slot(spec,
                         [HPySlot_Slot.HPy_tp_traverse, HPySlot_Slot.HPy_tp_destroy])
        attach_legacy_slots_to_type(space, w_result, spec.c_legacy_slots, needs_hpytype_dealloc)
    if spec.c_defines:
        add_slot_defs(handles, w_result, spec.c_defines)
    check_inheritance_constraints(space, w_result)
    return handles.new(w_result)

@specialize.arg(0)
def add_slot_defs(handles, w_result, c_defines):
    from .interp_module import get_doc  # avoid circular import
    space = handles.space
    p = c_defines
    i = 0
    HPyDef_Kind = llapi.cts.gettype('HPyDef_Kind')
    rbp = llapi.cts.cast('HPyFunc_releasebufferproc', 0)
    while p[i]:
        kind = rffi.cast(lltype.Signed, p[i].c_kind)
        if kind == HPyDef_Kind.HPyDef_Kind_Slot:
            hpyslot = llapi.cts.cast('_pypy_HPyDef_as_slot*', p[i]).c_slot
            slot_num = rffi.cast(lltype.Signed, hpyslot.c_slot)
            if slot_num == HPySlot_Slot.HPy_bf_releasebuffer:
                rbp = llapi.cts.cast('HPyFunc_releasebufferproc',
                                     hpyslot.c_impl)
            else:
                fill_slot(handles, w_result, hpyslot)
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
            add_member(space, w_result, hpymember)
        elif kind == HPyDef_Kind.HPyDef_Kind_GetSet:
            hpygetset = llapi.cts.cast('_pypy_HPyDef_as_getset*', p[i]).c_getset
            add_getset(handles, w_result, hpygetset)
        else:
            raise oefmt(space.w_ValueError, "Unspported HPyDef.kind: %d", kind)
        i += 1
    if rbp:
        w_buffer_wrapper = w_result.getdictvalue(space, '__buffer__')
        # XXX: this is horrible :-(
        getbuffer_cls = get_slot_cls(handles, W_wrap_getbuffer)
        if w_buffer_wrapper and isinstance(w_buffer_wrapper, getbuffer_cls):
            w_buffer_wrapper.rbp = rbp

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
        space, w_typetype, name, bases_w, dict_w, basicsize, is_legacy):
    pos = surrogate_in_utf8(name)
    if pos >= 0:
        raise oefmt(space.w_ValueError, "can't encode character in position "
                    "%d, surrogates not allowed", pos)

    w_type = W_HPyTypeObject(
        space, name, bases_w or [space.w_object], dict_w, basicsize, is_legacy)
    w_type.ready()
    return w_type

def _create_instance(space, w_type):
    # w_type = space.interp_w(W_HPyTypeObject, w_type)
    w_result = space.allocate_instance(W_HPyObject, w_type)
    if isinstance(w_type, W_HPyTypeObject):
        w_hpybase = w_type
    else:
        # a subclass?
        assert isinstance(w_type, W_TypeObject)
        for w_b in w_type.bases_w:
            if isinstance(w_b, W_HPyTypeObject):
                w_hpybase = w_b
                break
        else:
            # Can this ever happen?
            raise oefmt(space.w_TypeError, "bad call to __new__")
    w_result.space = space
    w_result.hpy_storage = storage_alloc(w_hpybase.basicsize)
    w_result.hpy_storage.tp_traverse = w_hpybase.tp_traverse
    if w_hpybase.tp_destroy or w_hpybase.tp_finalize:
        w_result.register_finalizer(space)
    if w_hpybase.has_tp_dealloc:
        # legacy: create a pyobj with refcnt == 0 so that when w_result
        # is collected, the pyobj's ob_type.tp_dealloc will be called
        if not hasattr(space, 'is_fake_objspace'):
            # the following lines break test_ztranslation :(
            as_pyobj(space, w_result)
    return w_result

descr_new = interp2app(_create_instance)

@specialize.memo()
def get_default_new(space):
    return descr_new.get_function(space)


@API.func("HPy HPyType_GenericNew(HPyContext *ctx, HPy type, HPy *args, HPy_ssize_t nargs, HPy kw)")
def HPyType_GenericNew(space, handles, ctx, h_type, args, nargs, kw):
    w_type = handles.deref(h_type)
    w_result = _create_instance(space, w_type)
    return handles.new(w_result)
