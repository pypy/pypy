from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_IntType(W_TypeObject):

    typename = 'int'

registerimplementation(W_IntType)


def type_new__IntType_IntType(space, w_basetype, w_inttype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    arglen = len(args)
    
    if arglen == 0:
        return space.newint(0), True
    elif arglen > 2:
        raise OperationError(space.w_TypeError,
                 space.wrap("int() takes at most 2 arguments"))
    elif space.is_true(space.issubtype(space.type(args[0]), space.w_str)):
        try:
            if arglen == 1:
                return space.newint(int(space.unwrap(args[0]))), True
            else:
                return space.newint(int(space.unwrap(args[0]),space.unwrap(args[1]))), True
        except TypeError, e:
            raise OperationError(space.w_TypeError,
                         space.wrap(str(e)))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                         space.wrap(str(e)))
        except OverflowError, e:
            raise OperationError(space.w_OverflowError,
                         space.wrap(str(e)))
    elif arglen == 2:
        raise OperationError(space.w_TypeError,
             space.wrap("int() can't convert non-string with explicit base"))
    else:
        return space.int(args[0]), True

register_all(vars())
