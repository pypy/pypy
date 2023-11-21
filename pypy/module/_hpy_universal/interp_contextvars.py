from rpython.rtyper.lltypesystem import rffi
from pypy.interpreter.error import OperationError
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import llapi

@API.func("HPy HPyContextVar_New(HPyContext *ctx, const char *name, HPy default_value)")
def HPyContextVar_New(space, handles, ctx, name, h_default):
    if name:
        w_str = space.newbytes(rffi.constcharp2str(name))
        w_name = space.call_method(w_str, 'decode', space.newtext("utf-8"))
    else:
        w_name = space.newtext('')
    if h_default:
        w_def = handles.deref(h_default)
        w_ret = space.appexec([w_name, w_def], """(name, default):
            from _contextvars import ContextVar
            return ContextVar(name, default=default)
            """)
    else:
        w_ret = space.appexec([w_name], """(name,):
            from _contextvars import ContextVar
            return ContextVar(name)
            """)
    return handles.new(w_ret)

@API.func("HPy HPyContextVar_Set(HPyContext *ctx, HPy context_var, HPy value)")
def HPyContextVar_Set(space, handles, ctx, h_ovar, h_val):
    w_ovar = handles.deref(h_ovar)
    w_val = handles.deref(h_val)
    w_ret = space.appexec([w_ovar, w_val], """(ovar, val):
        from _contextvars import ContextVar
        if not isinstance(ovar, ContextVar):
            raise TypeError('an instance of ContextVar was expected') 
        return ovar.set(val)
        """)
    return handles.new(w_ret)

@API.func("int HPyContextVar_Get(HPyContext *ctx, HPy context_var, HPy default_value, HPy *result)", error_value=API.int(-1))
def HPyContextVar_Get(space, handles, ctx,  h_ovar, h_default, val):
    w_ovar = handles.deref(h_ovar)
    if h_default:
        w_def = handles.deref(h_default)
        w_ret = space.appexec([w_ovar, w_def], """(ovar, default):
            from _contextvars import ContextVar
            if not isinstance(ovar, ContextVar):
                raise TypeError('an instance of ContextVar was expected') 
            return ovar.get(default)
        """)
    else:
        try:
            w_ret = space.appexec([w_ovar], """(ovar,):
                from _contextvars import ContextVar
                if not isinstance(ovar, ContextVar):
                    raise TypeError('an instance of ContextVar was expected') 
                return ovar.get()
            """)
        except OperationError as e:
            if e.match(space, space.w_LookupError):
                val[0] = llapi.cts.cast("HPy", 0)
                return API.int(0)
            raise e
    h = handles.new(w_ret)
    val[0] = h 
    return API.int(0)
