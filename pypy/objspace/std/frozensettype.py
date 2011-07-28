from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM


frozenset_copy                  = SMM('copy', 1,
                                      doc='Return a shallow copy of a set.')
frozenset_difference            = SMM('difference', 1, varargs_w=True,
                                      doc='Return a new set with elements in'
                                          ' the set that are not in the others.')
frozenset_intersection          = SMM('intersection', 1, varargs_w=True,
                                      doc='Return a new set with elements common'
                                          ' to the set and all others.')
frozenset_issubset              = SMM('issubset', 2,
                                      doc='Report whether another set contains'
                                          ' this set.')
frozenset_issuperset            = SMM('issuperset', 2,
                                      doc='Report whether this set contains'
                                          ' another set.')
frozenset_symmetric_difference  = SMM('symmetric_difference', 2,
                                      doc='Return the symmetric difference of'
                                          ' two sets as a new set.\n\n(i.e.'
                                          ' all elements that are in exactly'
                                          ' one of the sets.)')
frozenset_union                 = SMM('union', 1, varargs_w=True,
                                      doc='Return a new set with elements'
                                          ' from the set and all others.')
frozenset_reduce                = SMM('__reduce__',1,
                                      doc='Return state information for'
                                          ' pickling.')
# 2.6 methods
frozenset_isdisjoint            = SMM('isdisjoint', 2,
                                      doc='Return True if two sets have a'
                                          ' null intersection.')

register_all(vars(), globals())

def descr__frozenset__new__(space, w_frozensettype,
                            w_iterable=gateway.NoneNotWrapped):
    from pypy.objspace.std.setobject import W_FrozensetObject
    if (space.is_w(w_frozensettype, space.w_frozenset) and
        w_iterable is not None and type(w_iterable) is W_FrozensetObject):
        return w_iterable
    w_obj = space.allocate_instance(W_FrozensetObject, w_frozensettype)
    W_FrozensetObject.__init__(w_obj, space, w_iterable)
    return w_obj

frozenset_typedef = StdTypeDef("frozenset",
    __doc__ = """frozenset(iterable) --> frozenset object

Build an immutable unordered collection.""",
    __new__ = gateway.interp2app(descr__frozenset__new__),
    )

frozenset_typedef.registermethods(globals())
