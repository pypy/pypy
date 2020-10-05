from .apiset import API
from . import handles

@API.func('HPy HPyTuple_FromArray(HPyContext ctx, HPy items[], HPy_ssize_t n)')
def HPyTuple_FromArray(space, ctx, items, n):
    items_w = [None] * n
    for i in range(n):
        items_w[i] = handles.deref(space, items[i])
    w_result = space.newtuple(items_w)
    return handles.new(space, w_result)
