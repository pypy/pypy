from pypy.interpreter.error import OperationError
from pypy.objspace.std.objspace import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, newmethod
from pypy.objspace.std.stdtypedef import StdObjSpaceMultiMethod as SMM
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter import gateway
from pypy.objspace.std.model import WITHSET

set_add                         = SMM('add', 2)
set_clear                       = SMM('clear', 1)
set_copy                        = SMM('copy', 1)
set_difference                  = SMM('difference', 2)
set_difference_update           = SMM('difference_update', 2)
set_discard                     = SMM('discard', 2)
set_intersection                = SMM('intersection', 2)
set_intersection_update         = SMM('intersection_update', 2)
set_issubset                    = SMM('issubset', 2)
set_issuperset                  = SMM('issuperset', 2)
set_pop                         = SMM('pop', 1)
set_remove                      = SMM('remove', 2)
set_symmetric_difference        = SMM('symmetric_difference', 2)
set_symmetric_difference_update = SMM('symmetric_difference_update', 2)
set_union                       = SMM('union', 2)
set_update                      = SMM('update', 2)

register_all(vars(), globals())

def descr__set__new__(space, w_settype, w_iterable=NoneNotWrapped):
    from pypy.objspace.std.setobject import W_SetObject
    if w_iterable is None:
        w_iterable = space.newtuple([])
    w_obj = space.allocate_instance(W_SetObject, w_settype)
    W_SetObject.__init__(w_obj, space, w_iterable)

    return w_obj

set_typedef = StdTypeDef("set",
    __doc__ = """set(iterable) --> set object

Build an unordered collection.""",
    __new__ = newmethod(descr__set__new__),
    )

set_typedef.registermethods(globals())

setiter_typedef = StdTypeDef("setiterator")
