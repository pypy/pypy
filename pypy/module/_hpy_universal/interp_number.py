from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles


@API.func("HPy HPy_Add(HPyContext ctx, HPy x, HPy y)")
def HPy_Add(space, ctx, h1, h2):
    w_obj1 = handles.deref(space, h1)
    w_obj2 = handles.deref(space, h2)
    w_result = space.add(w_obj1, w_obj2)
    return handles.new(space, w_result)
