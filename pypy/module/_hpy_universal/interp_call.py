from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import oefmt
from .apiset import API

def Vectorcall_NARGS(n):
    PY_VECTORCALL_ARGUMENTS_OFFSET = 1 << (8 * rffi.sizeof(rffi.SIZE_T) - 1)
    return n & ~PY_VECTORCALL_ARGUMENTS_OFFSET

def obj_and_tuple_from_h_array(handles, h_args, n_minus_1):
    args_w = [None] * n_minus_1
    for i in range(n_minus_1):
        args_w[i] = handles.deref(h_args[i + 1])
    return handles.deref(h_args[0]), args_w

@API.func("HPy HPy_CallTupleDict(HPyContext *ctx, HPy callable, HPy args, HPy kw)")
def HPy_CallTupleDict(space, handles, ctx, h_callable, h_args, h_kw):
    w_callable = handles.deref(h_callable)
    w_args = handles.deref(h_args) if h_args else None
    w_kw = handles.deref(h_kw) if h_kw else None

    # Check the types here, as space.call would allow any iterable/mapping
    if w_args and not space.isinstance_w(w_args, space.w_tuple):
        raise oefmt(space.w_TypeError,
            "HPy_CallTupleDict requires args to be a tuple or null handle")
    if w_kw and not space.isinstance_w(w_kw, space.w_dict):
        raise oefmt(space.w_TypeError,
            "HPy_CallTupleDict requires kw to be a dict or null handle")

    # Note: both w_args and w_kw are allowed to be None
    w_result = space.call(w_callable, w_args, w_kw)
    return handles.new(w_result)

@API.func("HPy HPy_CallMethod(HPyContext *ctx, HPy name, const HPy* args, size_t nargs, HPy kwnames)")
def HPy_CallMethod(space, handles, ctx, h_name, h_argsp, nargs, h_kwargs):
    # h_kwargs is a list of names, h_argsp has nargs plus len(h_kwargs) values
    if not h_kwargs:
        n_kwargs = 0
        w_kwargs = None
    else:
        w_kwargs = handles.deref(h_kwargs)
        n_kwargs = space.len_w(w_kwargs)
    w_name = handles.deref(h_name)
    n = Vectorcall_NARGS(nargs)
    n_minus_1 = n - 1
    if n_minus_1 < 0:
        raise oefmt(space.w_ValueError, "n<1 in call to PyObject_VectorcallMethod")
    w_obj, args_w = obj_and_tuple_from_h_array(handles, h_argsp, n_minus_1 + n_kwargs)
    if w_kwargs is None:
        # fast path. Cannot use call_method(... *args_w)
        name = space.text_w(w_name)
        if n_minus_1 == 0:
            w_result = space.call_method(w_obj, name)
        elif n_minus_1 == 1:
            w_result = space.call_method(w_obj, name, args_w[0])
        elif n_minus_1 == 2:
            w_result = space.call_method(w_obj, name, args_w[0], args_w[1])
        elif n_minus_1 == 3:
            w_result = space.call_method(w_obj, name, args_w[0], args_w[1], args_w[2])
        else:
            w_meth = space.getattr(w_obj, w_name)
            w_result = space.call(w_meth, space.newtuple(args_w))
    else:
        w_dict = space.newdict()
        for i in range(n_kwargs):
            w_v =  args_w[i + n_minus_1]
            w_k = space.getitem(w_kwargs, space.newint(i))
            space.setitem(w_dict, w_k, w_v)
        w_meth = space.getattr(w_obj, w_name)
        w_result = space.call(w_meth, space.newtuple(args_w[:n_minus_1]), w_dict)
    return handles.new(w_result)


@API.func("HPy HPy_Call(HPyContext *ctx, HPy callable, const HPy *args, size_t nargs, HPy kwnames)")
def HPy_Call(space, handles, ctx, h_callable, h_argsp, nargs, h_kwargs):
    # h_kwargs is a list of names
    w_callable = handles.deref(h_callable)
    if not h_kwargs:
        n_kwargs = 0
        w_kwargs = None
    else:
        w_kwargs = handles.deref(h_kwargs)
        n_kwargs = space.len_w(w_kwargs)
    n = Vectorcall_NARGS(nargs)
    args_w = [None] * (n + n_kwargs)
    for i in range(n + n_kwargs):
        args_w[i] = handles.deref(h_argsp[i])
    if w_kwargs is None:
        w_result = space.call(w_callable, space.newtuple(args_w))
    else:
        w_dict = space.newdict()
        for i in range(n_kwargs):
            w_v =  args_w[i + n]
            w_k = space.getitem(w_kwargs, space.newint(i))
            space.setitem(w_dict, w_k, w_v)
        w_result = space.call(w_callable, space.newtuple(args_w[:n]), w_dict)
    return handles.new(w_result)


