from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module.hpy_universal.apiset import API
from pypy.module.hpy_universal import handles


@API.func("HPy HPy_FromPyObject(HPyContext ctx, void *obj)")
def HPy_FromPyObject(space, ctx, obj):
    from pypy.module.cpyext import pyobject
    w_obj = pyobject.from_ref(space, rffi.cast(pyobject.PyObject, obj))
    return handles.new(space, w_obj)

@API.func("void *HPy_AsPyObject(HPyContext ctx, HPy h)")
def HPy_AsPyObject(space, ctx, h):
    import pdb;pdb.set_trace()
