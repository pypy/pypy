from pypy.interpreter.error import oefmt
from .apiset import API
from . import handles

@API.func("HPy HPy_CallTupleDict(HPyContext ctx, HPy callable, HPy args, HPy kw)")
def HPy_CallTupleDict(space, state, ctx, h_callable, h_args, h_kw):
    w_callable = state.handles.deref(h_callable)
    w_args = state.handles.deref(h_args) if h_args else None
    w_kw = state.handles.deref(h_kw) if h_kw else None

    # Check the types here, as space.call would allow any iterable/mapping
    if w_args and not space.isinstance_w(w_args, space.w_tuple):
        raise oefmt(space.w_TypeError,
            "HPy_CallTupleDict requires args to be a tuple or null handle")
    if w_kw and not space.isinstance_w(w_kw, space.w_dict):
        raise oefmt(space.w_TypeError,
            "HPy_CallTupleDict requires kw to be a dict or null handle")

    # Note: both w_args and w_kw are allowed to be None
    w_result = space.call(w_callable, w_args, w_kw)
    return state.handles.new(w_result)
