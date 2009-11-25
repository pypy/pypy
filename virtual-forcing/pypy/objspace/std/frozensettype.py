from pypy.interpreter.error import OperationError
from pypy.objspace.std.objspace import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, newmethod
from pypy.objspace.std.stdtypedef import SMM
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter import gateway

frozenset_copy                  = SMM('copy', 1,
                                      doc='Return a shallow copy of a set.')
frozenset_difference            = SMM('difference', 2,
                                      doc='Return the difference of two sets'
                                          ' as a new set.\n\n(i.e. all'
                                          ' elements that are in this set but'
                                          ' not the other.)')
frozenset_intersection          = SMM('intersection', 2,
                                      doc='Return the intersection of two sets'
                                          ' as a new set.\n\n(i.e. all'
                                          ' elements that are in both sets.)')
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
frozenset_union                 = SMM('union', 2,
                                      doc='Return the union of two sets as a'
                                          ' new set.\n\n(i.e. all elements'
                                          ' that are in either set.)')
frozenset_reduce                = SMM('__reduce__',1,
                                      doc='Return state information for'
                                          ' pickling.')

register_all(vars(), globals())

def descr__frozenset__new__(space, w_frozensettype, w_iterable=NoneNotWrapped):
    from pypy.objspace.std.setobject import W_FrozensetObject
    from pypy.objspace.std.setobject import _is_frozenset_exact
    if (space.is_w(w_frozensettype, space.w_frozenset) and
        _is_frozenset_exact(w_iterable)):
        return w_iterable
    w_obj = space.allocate_instance(W_FrozensetObject, w_frozensettype)
    W_FrozensetObject.__init__(w_obj, space, None)

    return w_obj

frozenset_typedef = StdTypeDef("frozenset",
    __doc__ = """frozenset(iterable) --> frozenset object

Build an immutable unordered collection.""",
    __new__ = newmethod(descr__frozenset__new__),
    )

frozenset_typedef.registermethods(globals())
