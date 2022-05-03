from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API

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

    def store(self, pf, w_obj):
        # we need an ID to uniquely identify the HPyField pointed by pf: we
        # can just use its address. If later another object has the same
        # HPyField* we can safely override it, because it means that the
        # original object has died.
        #
        # NOTE: with he current strategy, self._fields is never cleared so an
        # HPyField_Store keeps the object alive forever. That's bad but we
        # don't care for now, since it's used only by a few tests.
        unique_id = rffi.cast(lltype.Signed, pf)
        self._fields[unique_id] = w_obj
        pf[0] = unique_id

    def load(self, f):
        if f not in self._fields:
            # we are trying to read a field which was never written to: this is basically a segfault :)
            assert False, 'boom'
        return self._fields[f]

_STORAGE = UntranslatedHPyFieldStorage()


@API.func("void HPyField_Store(HPyContext *ctx, HPy h_target, HPyField *pf, HPy h)")
def HPyField_Store(space, handles, ctx, h_target, pf, h):
    if we_are_translated():
        assert False # XXX
    #
    w_obj = handles.deref(h)
    _STORAGE.store(pf, w_obj)

@API.func("HPy HPyField_Load(HPyContext *ctx, HPy source_object, HPyField source_field)")
def HPyField_Load(space, handles, ctx, h_source, f):
    if we_are_translated():
        assert False # XXX
    w_obj = _STORAGE.load(f)
    return handles.new(w_obj)
