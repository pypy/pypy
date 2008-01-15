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


def proxymaker(space, opname, parentfn):
    def fn(*args_w):
        ec = space.getexecutioncontext()
        if ec.w_reflectivespace is not None:
            w_rspace = ec.w_reflectivespace
            ec.w_reflectivespace = None
            try:
                w_f = space.getattr(w_rspace, space.wrap(opname))
            except OperationError, e:
                if not e.match(space, space.w_AttributeError):
                    raise
            else:
                w_res = space.call_function(w_f, *args_w)
                ec.w_reflectivespace = w_rspace
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

