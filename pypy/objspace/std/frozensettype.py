from pypy.interpreter.error import OperationError
from pypy.objspace.std.objspace import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, newmethod
from pypy.objspace.std.stdtypedef import StdObjSpaceMultiMethod as SMM
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter import gateway
from pypy.objspace.std.model import WITHSET

frozenset_copy                  = SMM('copy', 1)
frozenset_difference            = SMM('difference', 2)
frozenset_intersection          = SMM('intersection', 2)
frozenset_issubset              = SMM('issubset', 2)
frozenset_issuperset            = SMM('issuperset', 2)
frozenset_symmetric_difference  = SMM('symmetric_difference', 2)
frozenset_union                 = SMM('union', 2)
frozenset_reduce                = SMM('__reduce__',1)

register_all(vars(), globals())

def descr__frozenset__new__(space, w_frozensettype, w_iterable=NoneNotWrapped):
    from pypy.objspace.std.setobject import W_FrozensetObject
    from pypy.objspace.std.setobject import _is_frozenset_exact
    if _is_frozenset_exact(w_iterable):
        return w_iterable
    w_obj = space.allocate_instance(W_FrozensetObject, w_frozensettype)
    W_FrozensetObject.__init__(w_obj, None)

    return w_obj

frozenset_typedef = StdTypeDef("frozenset",
    __doc__ = """frozenset(iterable) --> frozenset object

Build an immutable unordered collection.""",
    __new__ = newmethod(descr__frozenset__new__),
    )

frozenset_typedef.custom_hash = True
frozenset_typedef.registermethods(globals())
