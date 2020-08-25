from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import widen
from rpython.rlib import rgc
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.module.cpyext import pyobject
from pypy.module.cpyext.methodobject import PyMethodDef, PyCFunction
from pypy.module.cpyext.modsupport import convert_method_defs
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles
from pypy.module._hpy_universal import llapi

@API.func("HPy HPy_FromPyObject(HPyContext ctx, void *obj)", cpyext=True)
def HPy_FromPyObject(space, ctx, obj):
    w_obj = pyobject.from_ref(space, rffi.cast(pyobject.PyObject, obj))
    return handles.new(space, w_obj)

@API.func("void *HPy_AsPyObject(HPyContext ctx, HPy h)", cpyext=True)
def HPy_AsPyObject(space, ctx, h):
    w_obj = handles.deref(space, h)
    pyobj = pyobject.make_ref(space, w_obj)
    return rffi.cast(rffi.VOIDP, pyobj)


def attach_legacy_methods(space, hpymethods, w_mod, modname):
    """
    Convert HPyMethodDef[] into PyMethodDef[], and wrap the methods into the
    proper cpyext.W_*Function objects
    """
    from pypy.module.cpyext.api import cts as cpyts
    methods = cpyts.cast('PyMethodDef*', hpymethods)

    # convert hpymethods into a C array of PyMethodDef
    dict_w = {}
    convert_method_defs(space, dict_w, methods, None, w_mod, modname)

    for key, w_func in dict_w.items():
        space.setattr(w_mod, space.newtext(key), w_func)

    # transfer the ownership of pymethods to W_CPyStaticData
    w_static_data = W_CPyStaticData(space, methods)
    space.setattr(w_mod, space.newtext("__cpy_static_data__"), w_static_data)


class W_CPyStaticData(W_Root):
    """
    An object which owns the various C data structures which we need to create
    for compatibility with cpyext.
    """

    def __init__(self, space, pymethods):
        self.space = space
        self.pymethods = pymethods # PyMethodDef[]

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self.pymethods, flavor='raw')

    def repr(self):
        return self.space.newtext("<CpyStaticData>")

W_CPyStaticData.typedef = TypeDef(
    '_hpy_universal.CPyStaticData',
    __module__ = '_hpy_universal',
    __name__ = '<CPyStaticData>',
    __repr__ = interp2app(W_CPyStaticData.repr),
    )
W_CPyStaticData.typedef.acceptable_as_base_class = False
