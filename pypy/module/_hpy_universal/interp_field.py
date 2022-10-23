from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import rgc
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

    def store(self, pf, handles, h):
        # we need an ID to uniquely identify the HPyField pointed by pf: we
        # can just use its address. If later another object has the same
        # HPyField* we can safely override it, because it means that the
        # original object has died.
        #
        # NOTE: with he current strategy, self._fields is never cleared so an
        # HPyField_Store keeps the object alive forever. That's bad but we
        # don't care for now, since it's used only by a few tests.
        unique_id = llapi.cts.cast('long', pf)
        if h == 0:
            pf[0] = 0
            self._fields.pop(unique_id, None)
        else:
            w_obj = handles.deref(h)
            pf[0] = unique_id
            self._fields[unique_id] = w_obj

    def load(self, handles, f):
        if f not in self._fields:
            # we are trying to read a field which was never written to: this
            # is basically a segfault :)
            assert False, 'boom'
        w_obj = self._fields[f]
        return handles.new(w_obj)

_STORAGE = UntranslatedHPyFieldStorage()


@API.func("void HPyField_Store(HPyContext *ctx, HPy h_target, HPyField *pf, HPy h)")
def HPyField_Store(space, handles, ctx, h_target, pf, h):
    if not we_are_translated():
        # just for tests
        _STORAGE.store(pf, handles, h)
        return
    #
    # real implementation
    if h == handles.NULL:
        pf[0] = 0
    else:
        w_target = handles.deref(h_target)
        ll_assert(isinstance(w_target, W_HPyObject), 'h_target is not a valid HPy object')
        assert isinstance(w_target, W_HPyObject)
        rgc.ll_writebarrier(w_target.hpy_storage)
        #
        w_obj = handles.deref(h)
        gcref = rgc.cast_instance_to_gcref(w_obj)
        pf[0] = rffi.cast(lltype.Signed, gcref)


@API.func("HPy HPyField_Load(HPyContext *ctx, HPy source_object, HPyField source_field)")
def HPyField_Load(space, handles, ctx, h_source, f):
    if not we_are_translated():
        # just for tests
        return _STORAGE.load(handles, f)
    #
    # real implementation
    gcref = rffi.cast(llmemory.GCREF, f)
    w_obj = rgc.try_cast_gcref_to_instance(W_Root, gcref)
    # if w_obj is None it means that the gcref didn't contain a W_Root, but
    # this should not be possible
    assert w_obj is not None
    return handles.new(w_obj)

def is_hpy_object(w_obj):
    return isinstance(w_obj, W_HPyObject)

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
        w_type.tp_traverse(w_obj.get_raw_data(), ll_collect_fields, NULL)
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
    unique_id = llapi.cts.cast('long', f)
    w_obj = _STORAGE._fields[unique_id]
    _collect_fields.allfields.append(w_obj)
    return API.int(0)
_collect_fields.allfields = []
