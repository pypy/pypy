from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM

set_add                         = SMM('add', 2,
                                      doc='Add an element to a set.\n\nThis'
                                          ' has no effect if the element is'
                                          ' already present.')
set_clear                       = SMM('clear', 1,
                                      doc='Remove all elements from this set.')
set_copy                        = SMM('copy', 1,
                                      doc='Return a shallow copy of a set.')
set_difference                  = SMM('difference', 2,
                                      doc='Return the difference of two sets'
                                          ' as a new set.\n\n(i.e. all'
                                          ' elements that are in this set but'
                                          ' not the other.)')
set_difference_update           = SMM('difference_update', 2,
                                      doc='Remove all elements of another set'
                                          ' from this set.')
set_discard                     = SMM('discard', 2,
                                      doc='Remove an element from a set if it'
                                          ' is a member.\n\nIf the element is'
                                          ' not a member, do nothing.')
set_intersection                = SMM('intersection', 2,
                                      doc='Return the intersection of two sets'
                                          ' as a new set.\n\n(i.e. all'
                                          ' elements that are in both sets.)')
set_intersection_update         = SMM('intersection_update', 2,
                                      doc='Update a set with the intersection'
                                          ' of itself and another.')
set_issubset                    = SMM('issubset', 2,
                                      doc='Report whether another set contains'
                                          ' this set.')
set_issuperset                  = SMM('issuperset', 2,
                                      doc='Report whether this set contains'
                                          ' another set.')
set_pop                         = SMM('pop', 1,
                                      doc='Remove and return an arbitrary set'
                                          ' element.')
set_remove                      = SMM('remove', 2,
                                      doc='Remove an element from a set; it'
                                          ' must be a member.\n\nIf the'
                                          ' element is not a member, raise a'
                                          ' KeyError.')
set_symmetric_difference        = SMM('symmetric_difference', 2,
                                      doc='Return the symmetric difference of'
                                          ' two sets as a new set.\n\n(i.e.'
                                          ' all elements that are in exactly'
                                          ' one of the sets.)')
set_symmetric_difference_update = SMM('symmetric_difference_update', 2,
                                      doc='Update a set with the symmetric'
                                          ' difference of itself and another.')
set_union                       = SMM('union', 1, varargs_w=True,
                                      doc='Return a new set with elements'
                                          ' from the set and all others.')
set_update                      = SMM('update', 2,
                                      doc='Update a set with the union of'
                                          ' itself and another.')
set_reduce                      = SMM('__reduce__',1,
                                      doc='Return state information for'
                                          ' pickling.')
# 2.6 methods
set_isdisjoint                  = SMM('isdisjoint', 2,
                                      doc='Return True if two sets have a'
                                          ' null intersection.')

register_all(vars(), globals())

def descr__new__(space, w_settype, __args__):
    from pypy.objspace.std.setobject import W_SetObject, newset
    w_obj = space.allocate_instance(W_SetObject, w_settype)
    W_SetObject.__init__(w_obj, space, newset(space))
    return w_obj

set_typedef = StdTypeDef("set",
    __doc__ = """set(iterable) --> set object

Build an unordered collection.""",
    __new__ = gateway.interp2app(descr__new__, unwrap_spec=[gateway.ObjSpace,
                                                            gateway.W_Root,
                                                            gateway.Arguments]),
    __hash__ = None,
    )

set_typedef.registermethods(globals())

setiter_typedef = StdTypeDef("setiterator")
