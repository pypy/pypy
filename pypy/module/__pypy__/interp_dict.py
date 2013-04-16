
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import operationerrfmt, OperationError
from pypy.objspace.std.dictmultiobject import W_DictMultiObject

@unwrap_spec(type=str)
def newdict(space, type):
    if type == 'module':
        return space.newdict(module=True)
    elif type == 'instance':
        return space.newdict(instance=True)
    elif type == 'kwargs':
        return space.newdict(kwargs=True)
    elif type == 'strdict':
        return space.newdict(strdict=True)
    else:
        raise operationerrfmt(space.w_TypeError, "unknown type of dict %s",
                              type)

def dictstrategy(space, w_obj):
    if not isinstance(w_obj, W_DictMultiObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("expecting dict object"))
    return space.wrap('%r' % (w_obj.strategy,))
