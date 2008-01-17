from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.objspace import std
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.proxy import patch_space_in_place

def set_reflectivespace(space, w_reflectivespace):
    ec = space.getexecutioncontext()
    if space.is_w(w_reflectivespace, space.w_None):
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
    def user_hook(*args_w):
        w_rspace = get_reflective_space(space)
        if w_rspace is not None:
            try:
                try:
                    w_f = space.getattr(w_rspace, space.wrap(opname))
                except OperationError, e:
                    if not e.match(space, space.w_AttributeError):
                        raise
                else:
                    return space.call_function(w_f, *args_w)
            finally:
                reset_reflective_space(space, w_rspace)
        return None

    if opname == "newdict": # grr grr kwargs
        def fn(track_builtin_shadowing=False):
            w_obj = parentfn(track_builtin_shadowing)
            w_newobj = user_hook(w_obj)
            if w_newobj is not None:
                return w_newobj
            return w_obj
    elif opname.startswith("new"):
        def fn(*args):
            w_obj = parentfn(*args)
            w_newobj = user_hook(w_obj)
            if w_newobj is not None:
                return w_newobj
            return w_obj
    elif opname == "type":
        def fn(*args_w):
            w_obj = user_hook(*args_w)
            if w_obj is not None:
                if not isinstance(w_obj, W_TypeObject):
                    raise OperationError(
                        space.w_TypeError,
                        space.wrap("space.type must return a type object!"))
                return w_obj
            return parentfn(*args_w)
    else:
        def fn(*args_w):
            w_obj = user_hook(*args_w)
            if w_obj is not None:
                return w_obj
            return parentfn(*args_w)
    fn.func_name = opname
    return fn

class ReflectiveObjSpace(std.Space):
    def createexecutioncontext(self):
        ec = std.Space.createexecutioncontext(self)
        ec.w_reflectivespace = None
        return ec

def Space(*args, **kwds):
    space = ReflectiveObjSpace(*args, **kwds)
    patch_space_in_place(space, 'reflective', proxymaker)
    w___pypy__ = space.getbuiltinmodule("__pypy__")
    space.setattr(w___pypy__, space.wrap('set_reflectivespace'),
                  space.wrap(app_set_reflectivespace))
    return space

