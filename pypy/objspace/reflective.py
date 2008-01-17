from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.objspace import std
from pypy.objspace.proxy import patch_space_in_place

def set_reflectivespace(space, w_reflectivespace):
    ec = space.getexecutioncontext()
    if space.is_w(ec.w_reflectivespace, space.w_None):
        ec.w_reflectivespace = None
    else:
        ec.w_reflectivespace = w_reflectivespace
app_set_reflectivespace = gateway.interp2app(set_reflectivespace)

def get_reflective_space(space):
    ec = space.getexecutioncontext()
    if ec.w_reflectivespace is not None:
        w_rspace = ec.w_reflectivespace
        ec.w_reflectivespace = None
        return w_rspace
    return None

def reset_reflective_space(space, w_rspace):
    ec = space.getexecutioncontext()
    ec.w_reflectivespace = w_rspace


DontWrapMe = [
    'wrap',
    'str_w',
    'int_w',
    'float_w',
    'uint_w',
    'bigint_w',
    'unicode_w',
    'interpclass_w',
    'unwrap',
    'is_true',
    'is_w',
    'call_args',
    'marshal_w',
    ]

def proxymaker(space, opname, parentfn):
    if opname in DontWrapMe:
        return None
    elif opname == "newdict": # grr grr kwargs
        def fn(track_builtin_shadowing=False):
            w_obj = parentfn(track_builtin_shadowing)
            w_rspace = get_reflective_space(space)
            if w_rspace is not None:
                try:
                    w_f = space.getattr(w_rspace, space.wrap("newdict"))
                except OperationError, e:
                    if not e.match(space, space.w_AttributeError):
                        raise
                else:
                    w_obj = space.call_function(w_f, w_obj)
                    reset_reflective_space(space, w_rspace)
            return w_obj
    elif opname.startswith("new"):
        def fn(*args_w):
            w_obj = parentfn(*args_w)
            w_rspace = get_reflective_space(space)
            if w_rspace is not None:
                try:
                    w_f = space.getattr(w_rspace, space.wrap(opname))
                except OperationError, e:
                    if not e.match(space, space.w_AttributeError):
                        raise
                else:
                    w_obj = space.call_function(w_f, w_obj)
                    reset_reflective_space(space, w_rspace)
            return w_obj
    else:
        def fn(*args_w):
            ec = space.getexecutioncontext()
            w_rspace = get_reflective_space(space)
            if w_rspace is not None:
                try:
                    w_f = space.getattr(w_rspace, space.wrap(opname))
                except OperationError, e:
                    if not e.match(space, space.w_AttributeError):
                        raise
                else:
                    w_res = space.call_function(w_f, *args_w)
                    reset_reflective_space(space, w_rspace)
                    return w_res
            return parentfn(*args_w)
    fn.func_name = opname
    return fn

def createexecutioncontextmaker(space, parentfn):
    def createexecutioncontext():
        ec = parentfn()
        ec.w_reflectivespace = None
        return ec
    return createexecutioncontext

def Space(*args, **kwds):
    space = std.Space(*args, **kwds)
    space.createexecutioncontext = createexecutioncontextmaker(
        space, space.createexecutioncontext)
    space.getexecutioncontext().w_reflectivespace = None # patch the already built ec
    patch_space_in_place(space, 'reflective', proxymaker)
    w___pypy__ = space.getbuiltinmodule("__pypy__")
    space.setattr(w___pypy__, space.wrap('set_reflectivespace'),
                  space.wrap(app_set_reflectivespace))
    return space

