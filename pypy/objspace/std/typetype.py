from pypy.objspace.std.objspace import *
from pypy.objspace.std.register_all import register_all
from pypy.interpreter import eval
from typeobject import W_TypeObject


class NewMmFrame(eval.Frame):
    def run(self):
        "Call the __new__() method of typetype.py."
        mm = self.code.slice().get(self.space)
        args = self.fastlocals_w
        w_result, callinit = mm(*args)
        return w_result


class W_TypeType(W_TypeObject):
    """The single instance of this class is the object the user sees as
    '__builtin__.type'."""

    typename = 'type'

    # XXX this is worth tons of comments.
    # the four arguments are (T, S, args, kw) for the expression
    # T.__new__(S, *args, **kw).  There is no (known?) way to get it as
    # an unbound method, because 'type.__new__' means reading from the
    # instance 'type' of the class 'type', as opposed to reading from
    # the class 'type'.
    # Attention, this internally returns a tuple (w_result, flag),
    # where 'flag' specifies whether we would like __init__() to be called.
    type_new = MultiMethod('__new__', 2, varargs=True, keywords=True,
                                         mmframeclass=NewMmFrame)

registerimplementation(W_TypeType)

def type_new__TypeType_TypeType(space, w_basetype, w_typetype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 1:
        return space.type(args[0]), False   # don't call __init__() on that
    elif len(args) == 3:
        from usertype import W_UserType
        w_name, w_bases, w_dict = args
        w_usertype = W_UserType(space, w_name, w_bases, w_dict)
        return w_usertype, True
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("type() takes 1 or 3 arguments"))

register_all(vars())
