from pypy.interpreter import gateway, typedef, argument
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.objspace import std
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.proxy import patch_space_in_place

def set_reflectivespace(space, w_reflectivespace):
    ec = space.getexecutioncontext()
    if space.is_w(w_reflectivespace, space.w_None):
        ec.w_rspace = None
    else:
        ec.w_rspace = w_reflectivespace
app_set_reflectivespace = gateway.interp2app(set_reflectivespace)

def get_reflective_space(space):
    ec = space.getexecutioncontext()
    w_rspace = ec.w_rspace
    if w_rspace is not None:
        ec.w_rspace = None
        return w_rspace
    return None

def reset_reflective_space(space, w_rspace):
    ec = space.getexecutioncontext()
    ec.w_rspace = w_rspace

class W_SpaceAccess(Wrappable):
    def __init__(self, space, w_reflectivespace):
        self.space = space
        self.w_reflectivespace = w_reflectivespace

W_SpaceAccess_dict = {}

def get_spaceop_args(name):
    for opname, _, args, _ in ObjSpace.MethodTable:
        if opname == name:
            return args
    if opname == "is_true":
        return 1

def make_space_access_method(name, wrappedfn, parentfn):
    if name.startswith("new") or name.endswith("_w"):
        # those methods cannot call back to applevel, so no need to expose them
        return
    if name == "call_args":
        def func(self, space, w_func, args):
            w_old_reflectivespace = get_reflective_space(space)
            set_reflectivespace(space, self.w_reflectivespace)
            try:
                return parentfn(w_func, args)
            finally:
                reset_reflective_space(space, w_old_reflectivespace)
        unwrap_spec = ['self', ObjSpace, W_Root, argument.Arguments]
    elif name == "is_true":
        def func(self, space, w_obj):
            w_old_reflectivespace = get_reflective_space(space)
            set_reflectivespace(space, self.w_reflectivespace)
            try:
                if parentfn(w_obj):
                    return space.w_True
                return space.w_False
            finally:
                reset_reflective_space(space, w_old_reflectivespace)
        unwrap_spec = ['self', ObjSpace, W_Root]
    else:
        args = get_spaceop_args(name)
        if args == 1:
            def func(self, space, w_arg1):
                w_old_reflectivespace = get_reflective_space(space)
                set_reflectivespace(space, self.w_reflectivespace)
                try:
                    return parentfn(w_arg1)
                finally:
                    reset_reflective_space(space, w_old_reflectivespace)
        elif args == 2:
            def func(self, space, w_arg1, w_arg2):
                w_old_reflectivespace = get_reflective_space(space)
                set_reflectivespace(space, self.w_reflectivespace)
                try:
                    return parentfn(w_arg1, w_arg2)
                finally:
                    reset_reflective_space(space, w_old_reflectivespace)
        elif args == 3:
            def func(self, space, w_arg1, w_arg2, w_arg3):
                w_old_reflectivespace = get_reflective_space(space)
                set_reflectivespace(space, self.w_reflectivespace)
                try:
                    return parentfn(w_arg1, w_arg2, w_arg3)
                finally:
                    reset_reflective_space(space, w_old_reflectivespace)
        else:
            raise NotImplementedError
        unwrap_spec = ["self", ObjSpace] + [W_Root] * args
    func_name =  "descr_" + name
    func.func_name = func_name
    setattr(W_SpaceAccess, func_name, func)
    bound_func = getattr(W_SpaceAccess, func_name)
    W_SpaceAccess_dict[name] = gateway.interp2app(bound_func, unwrap_spec=unwrap_spec)


DontWrapMe = [
    'wrap',
    'interpclass_w',
    'unwrap',
    'marshal_w',
    'nonzero', # maps to is_true anyway
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
                    spaceaccess = W_SpaceAccess(space, w_rspace)
                    w_spaceaccess = space.wrap(spaceaccess)
                    return space.call_function(w_f, w_spaceaccess, *args_w)
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
    elif opname == "is_w":
        def fn(w_obj1, w_obj2):
            return space.is_true(space.is_(w_obj1, w_obj2))
    elif opname.endswith("_w"):
        def fn(w_obj):
            w_newobj = user_hook(w_obj)
            if w_newobj is not None:
                w_obj = w_newobj
            return parentfn(w_obj)
    elif opname == "call_args":
        def fn(w_callable, args):
            w_rspace = get_reflective_space(space)
            if w_rspace is not None:
                try:
                    try:
                        w_f = space.getattr(w_rspace, space.wrap(opname))
                    except OperationError, e:
                        if not e.match(space, space.w_AttributeError):
                            raise
                    else:
                        spaceaccess = W_SpaceAccess(space, w_rspace)
                        w_spaceaccess = space.wrap(spaceaccess)
                        # XXX argh, not terribly efficient
                        args = args.prepend(w_callable).prepend(w_spaceaccess)
                        w_args, w_kwargs = args.topacked()
                        return space.call(w_f, w_args, w_kwargs)
                finally:
                    reset_reflective_space(space, w_rspace)
            return parentfn(w_callable, args)
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
    elif opname == "is_true":
        def fn(w_obj):
            w_newobj = user_hook(w_obj)
            if w_newobj is not None:
                if w_newobj is space.w_True:
                    return True
                elif w_newobj is space.w_False:
                    return False
                raise OperationError(space.w_TypeError,
                                     space.wrap("is_true must return True or False"))
            return parentfn(w_obj)
    else:
        def fn(*args_w):
            w_obj = user_hook(*args_w)
            if w_obj is not None:
                return w_obj
            return parentfn(*args_w)
    make_space_access_method(opname, fn, parentfn)
    fn.func_name = opname
    return fn

class ReflectiveObjSpace(std.Space):
    def createexecutioncontext(self):
        ec = std.Space.createexecutioncontext(self)
        ec.w_rspace = None
        return ec

def Space(*args, **kwds):
    space = ReflectiveObjSpace(*args, **kwds)
    patch_space_in_place(space, 'reflective', proxymaker)
    w___pypy__ = space.getbuiltinmodule("__pypy__")
    space.setattr(w___pypy__, space.wrap('set_reflectivespace'),
                  space.wrap(app_set_reflectivespace))
    W_SpaceAccess.typedef = typedef.TypeDef("ObjSpace", **W_SpaceAccess_dict)
    return space

