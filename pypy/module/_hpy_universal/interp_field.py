from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import rgc, jit
from rpython.rlib.debug import ll_assert
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal.interp_type import W_HPyObject, W_HPyTypeObject

class UntranslatedHPyFieldStorage(object):
    """
    Proper support for HPyField is possible only after translation, because it
    needs a tight integration with the GC.

    For untranslated apptests, we use this small helper to keep track of which
    object is stored in every HPyField. We don't need anything fancy, just
    enough logic to make the tests work. In particular, we want to ensure that
    if we HPyField_Store() something, we can HPyField_Load() it later.
    """

    def __init__(self):
        self._fields = {}

    def _freeze_(self):
        raise Exception('You should not use UntranslatedHPyFieldStorage '
                        'from translated code')

    def store_w(self, pf, w_obj):
        # we need an ID to uniquely identify the HPyField pointed by pf: we
        # can just use its address. If later another object has the same
        # HPyField* we can safely override it, because it means that the
        # original object has died.
        #
        # NOTE: with he current strategy, self._fields is never cleared so an
        # HPyField_Store keeps the object alive forever. That's bad but we
        # don't care for now, since it's used only by a few tests.
        unique_id = rffi.cast(lltype.Signed, pf)
        pf[0] = unique_id
        self._fields[unique_id] = w_obj

    def delete(self, pf):
        unique_id = rffi.cast(lltype.Signed, pf)
        self._fields.pop(unique_id, None)
        pf[0] = 0

    def load_w(self, f):
        # returns the w_obj
        if f not in self._fields:
            # we are trying to read a field which was never written to: this
            # is basically a segfault :)
            assert False, 'boom'
        return self._fields[f]

_STORAGE = UntranslatedHPyFieldStorage()

@jit.dont_look_inside
def field_store_w(space, pf, w_target, w_value):
    ll_assert(isinstance(w_target, W_HPyObject), 'h_target is not a valid HPy object')
    assert isinstance(w_target, W_HPyObject)
    assert isinstance(w_value, W_Root)
    if not we_are_translated():
        _STORAGE.store_w(pf, w_value)
    else:
        storage = w_target._hpy_get_gc_storage(space)
        # Should never happen
        ll_assert(bool(storage.tp_traverse), "required tp_traverse function missing on storage")
        assert bool(storage.tp_traverse)
        rgc.ll_writebarrier(storage)
        #
        gcref = rgc.cast_instance_to_gcref(w_value)
        pf[0] = rffi.cast(lltype.Signed, gcref)


@jit.dont_look_inside
@API.func("void HPyField_Store(HPyContext *ctx, HPy h_target, HPyField *pf, HPy h)")
def HPyField_Store(space, handles, ctx, h_target, pf, h):
    # TODO: refactor this to use field_store_w, field_delete_w
    if not we_are_translated():
        # just for tests
        if h == handles.NULL:
            _STORAGE.delete(pf)
        else:
            w_obj = handles.deref(h)
            _STORAGE.store_w(pf, w_obj)
        return
    #
    # real implementation
    if h == handles.NULL:
        pf[0] = 0
    else:
        w_target = handles.deref(h_target)
        ll_assert(isinstance(w_target, W_HPyObject) or isinstance(w_target, W_HPyTypeObject), 'h_target is not a valid HPy object')
        assert (isinstance(w_target, W_HPyObject) or isinstance(w_target, W_HPyTypeObject))
        storage = w_target._hpy_get_gc_storage(space)
        # Should never happen
        ll_assert(bool(storage.tp_traverse), "required tp_traverse function missing on storage")
        assert bool(storage.tp_traverse)
        rgc.ll_writebarrier(storage)
        #
        w_obj = handles.deref(h)
        gcref = rgc.cast_instance_to_gcref(w_obj)
        pf[0] = rffi.cast(lltype.Signed, gcref)

@jit.dont_look_inside
def field_load_w(space, w_source, f):
    if we_are_translated():
        ll_assert(isinstance(w_source, W_HPyObject) or isinstance(w_source, W_HPyTypeObject), 'h_target is not a valid HPy object')
        assert (isinstance(w_source, W_HPyObject) or isinstance(w_source, W_HPyTypeObject))
        gcref = rffi.cast(llmemory.GCREF, f)
        w_obj = rgc.try_cast_gcref_to_instance(W_Root, gcref)
        # if w_obj is None it means that the gcref didn't contain a W_Root, but
        # this should not be possible
        assert w_obj is not None
    else:
        # just for tests
        w_obj = _STORAGE.load_w(f)
    return w_obj
    
def field_delete_w(pf):
    if we_are_translated():
        pf[0] = 0
    else:
        _STORAGE.delete(pf)


@API.func("HPy HPyField_Load(HPyContext *ctx, HPy source_object, HPyField source_field)")
def HPyField_Load(space, handles, ctx, h_source, f):
    w_source = handles.deref(h_source)
    w_obj = field_load_w(space, w_source, f)
    return handles.new(w_obj)

def is_hpy_object(w_obj):
    return isinstance(w_obj, W_HPyObject) or isinstance(w_obj, W_HPyTypeObject)

def hpy_get_referents(space, w_obj):
    """
    NOT_RPYTHON. Called by gc.get_referents, only for hpy objects and only for tests
    """
    w_type = space.type(w_obj)
    assert is_hpy_object(w_obj)
    assert isinstance(w_type, W_HPyTypeObject)
    if w_type.tp_traverse:
        ll_collect_fields = _collect_fields.get_llhelper(space)
        assert _collect_fields.allfields == []
        NULL = llapi.cts.cast('void *', 0)
        w_type.tp_traverse(w_obj._hpy_get_raw_storage(space), ll_collect_fields, NULL)
        result = _collect_fields.allfields
        _collect_fields.allfields = []
        return result


@API.func("int _collect_fields(HPyField *f, void *arg)",
          error_value=API.int(-1), is_helper=True)
def _collect_fields(space, handles, f, arg):
    """
    Only for tests, see hpy_get_referents
    """
    assert not we_are_translated()
    unique_id = rffi.cast(lltype.Signed, f)
    w_obj = _STORAGE._fields[unique_id]
    _collect_fields.allfields.append(w_obj)
    return API.int(0)
_collect_fields.allfields = []
