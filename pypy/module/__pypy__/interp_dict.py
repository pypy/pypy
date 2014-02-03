
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.objspace.std.dictmultiobject import W_DictMultiObject

@unwrap_spec(type=str)
def newdict(space, type):
    """ newdict(type)

    Create a normal dict with a special implementation strategy.

    type is a string and can be:

    * "module" - equivalent to some_module.__dict__

    * "instance" - equivalent to an instance dict with a not-changing-much
                   set of keys

    * "kwargs" - keyword args dict equivalent of what you get from **kwargs
                 in a function, optimized for passing around

    * "strdict" - string-key only dict. This one should be chosen automatically
    """
    if type == 'module':
        return space.newdict(module=True)
    elif type == 'instance':
        return space.newdict(instance=True)
    elif type == 'kwargs':
        return space.newdict(kwargs=True)
    elif type == 'strdict':
        return space.newdict(strdict=True)
    else:
        raise oefmt(space.w_TypeError, "unknown type of dict %s", type)

def dictstrategy(space, w_obj):
    """ dictstrategy(dict)

    show the underlaying strategy used by a dict object
    """
    if not isinstance(w_obj, W_DictMultiObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("expecting dict object"))
    return space.wrap('%r' % (w_obj.strategy,))
