from pypy.interpreter.error import OperationError
from pypy.objspace.std.objspace import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, newmethod
from pypy.objspace.std.stdtypedef import StdObjSpaceMultiMethod
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter import gateway
from pypy.objspace.std.model import WITHSET

def descr__set__new__(space, w_settype, w_iterable=NoneNotWrapped):
    from pypy.objspace.std.setobject import W_SetObject
    if w_iterable is None:
        w_iterable = space.newtuple([])
    elif (space.is_w(w_settype, space.w_set) and
            space.is_w(space.type(w_iterable), space.w_set)):
        return w_iterable
    w_obj = space.allocate_instance(W_SetObject, w_settype)
    W_SetObject.__init__(w_obj, space, w_iterable)

    return w_obj

def descr__frozenset__new__(space, w_frozensettype, w_iterable=NoneNotWrapped):
    from pypy.objspace.std.setobject import W_FrozensetObject
    if w_iterable is None:
        w_iterable = space.newtuple([])
    elif (space.is_w(w_frozensettype, space.w_frozenset) and
            space.is_w(space.type(w_iterable), space.w_frozenset)):
        return w_iterable
    w_obj = space.allocate_instance(W_FrozensetObject, w_frozensettype)
    W_FrozensetObject.__init__(w_obj, space, w_iterable)

    return w_obj

# some helper functions

def _extract_data_dict(space, w_left, w_right):
    assert (space.is_true(space.isinstance(w_left, space.w_set)) or 
        space.is_true(space.isinstance(w_left, space.w_frozenset)))
    if not (space.is_true(space.isinstance(w_right, space.w_set)) or 
            space.is_true(space.isinstance(w_right, space.w_frozenset))):
        w_right = space.newset(w_right)

    return w_left.data, w_right.data

def _dict_to_set(space, rpdict):
    return space.newset(space.newtuple(rpdict.keys()))

def _dict_to_frozenset(space, rpdict):
    return space.newfrozenset(space.newtuple(rpdict.keys()))

# helper functions for set operation on dicts

def _union_dict(space, ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    ld.update(rdict)
    return ld, rdict

def _difference_dict(space, ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    del_list_w = []
    for w_key in ld.iterkeys():
        if w_key in rdict:
            del_list_w.append(w_key)
    for w_key in del_list_w:
        del ld[w_key]

    return ld, rdict

def _intersection_dict(space, ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    del_list_w = []
    for w_key in ld.iterkeys():
        if w_key not in rdict:
            del_list_w.append(w_key)

    for w_key in del_list_w:
        del ld[w_key]

    return ld, rdict


def _symmetric_difference_dict(space, ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    del_list_w = []
    add_list_w = []
    for w_key in ld.iterkeys():
        if w_key in rdict:
            del_list_w.append(w_key)

    for w_key in rdict.iterkeys():
        if w_key not in ld:
            add_list_w.append(w_key)

    for w_key in del_list_w:
        del ld[w_key]

    for w_key in add_list_w:
        ld[w_key] = space.w_True

    return ld, rdict

def descr_update(space, w_self, w_iterable):
    """Update a set with the union of itself and another."""
    ld, rd = _extract_data_dict(space, w_self, w_iterable)
    new_ld, rd = _union_dict(space, ld, rd, True)
    return space.w_None

def descr_add(space, w_self, w_other):
    """Add an element to a set.

    This has no effect if the element is already present.
    """

    w_self.data[w_other] = space.w_True

def descr_copy_s(space, w_self):
    return space.newset(w_self)

def descr_copy_fs(space, w_self):
    return space.newfrozenset(w_self)

def descr_clear(space, w_self):
    w_self.data.clear()

def descr_difference_s(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _difference_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

def descr_difference_fs(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _difference_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)


def descr_difference_update(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _difference_dict(space, ld, rd, True)
    return space.w_None

def descr__set__eq__(space, w_self, w_other):
    if space.is_w(w_self, w_other):
        return space.w_True

    if len(w_self.data) != len(w_other.data):
        return space.w_False

    for w_key in w_self.data.iterkeys():
        if w_key not in w_other.data:
            return space.w_False
    return space.w_True

def descr__set__contains__(space, w_self, w_other):
    return space.newbool(w_other in w_self.data)

def descr_issubset(space, w_self, w_other):
    if space.is_w(w_self, w_other):
        return space.w_True

    if len(w_self.data) > len(w_other.data):
        return space.w_False

    for w_key in w_self.data:
        if w_key not in w_other.data:
            return space.w_False
    return space.w_True

def descr_issuperset(space, w_self, w_other):
    if space.is_w(w_self, w_other):
        return space.w_True

    if len(w_self.data) < len(w_other.data):
        return space.w_False

    for w_key in w_other.data:
        if w_key not in w_self.data:
            return space.w_False
    return space.w_True

def descr_discard(space, w_self, w_item):
    if w_item in w_self.data:
        del w_self.data[w_item]
    
def descr_remove(space, w_self, w_item):
    try:
        del w_self.data[w_item]
    except KeyError:
        raise OperationError(space.w_KeyError,
                space.call_method(w_item,'__repr__'))

def descr__set__hash__(space, w_self):
    raise OperationError(space.w_TypeError,
            space.wrap('set objects are unhashable'))

def descr_pop(space, w_self):
    if len(w_self.data) == 0:
        raise OperationError(space.w_KeyError,
                                space.wrap('pop from an empty set'))
    w_keys = w_self.data.keys()
    w_value = w_keys[0]
    del w_self.data[w_value]

    return w_value

def descr_intersection_s(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _intersection_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

def descr_intersection_fs(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _intersection_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)

def descr_intersection_update(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _intersection_dict(space, ld, rd, True)
    return space.w_None

def descr_symmetric_difference_s(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _symmetric_difference_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

def descr_symmetric_difference_fs(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _symmetric_difference_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)

def descr_symmetric_difference_update(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _symmetric_difference_dict(space, ld, rd, True)
    return space.w_None

def descr_union_s(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _union_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

def descr_union_fs(space, w_self, w_other):
    ld, rd = _extract_data_dict(space, w_self, w_other)
    new_ld, rd = _union_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)

def descr__set__len__(space, w_self):
    return space.newint(len(w_self.data))

def descr__set__iter__(space, w_self):
    from pypy.objspace.std import iterobject
    return iterobject.W_SeqIterObject(space, 
                                        space.newtuple(w_self.data.keys()))

set_typedef = StdTypeDef("set",
    __doc__ = """set(iterable) --> set object

Build an unordered collection.""",
    __new__ = newmethod(descr__set__new__),
    __eq__ = newmethod(descr__set__eq__),
    __contains__ = newmethod(descr__set__contains__),
    __len__ = newmethod(descr__set__len__),
    __iter__ = newmethod(descr__set__iter__),
    __hash__ = newmethod(descr__set__hash__),
    add = newmethod(descr_add),
    clear = newmethod(descr_clear),
    copy = newmethod(descr_copy_s),
    difference = newmethod(descr_difference_s),
    difference_update = newmethod(descr_difference_update),
    discard = newmethod(descr_discard),
    intersection = newmethod(descr_intersection_s),
    intersection_update = newmethod(descr_intersection_update),
    issubset = newmethod(descr_issubset),
    issuperset = newmethod(descr_issuperset),
    pop = newmethod(descr_pop),
    remove = newmethod(descr_remove),
    symmetric_difference = newmethod(descr_symmetric_difference_s),
    symmetric_difference_update = newmethod(descr_symmetric_difference_update),
    union = newmethod(descr_union_s),
    update = newmethod(descr_update),
    )

#set_typedef.registermethods(globals())

frozenset_typedef = StdTypeDef("frozenset",
    __doc__ = """frozenset(iterable) --> frozenset object

Build an immutable unordered collection.""",
    __new__ = newmethod(descr__frozenset__new__),
    __eq__ = newmethod(descr__set__eq__),
    __contains__ = newmethod(descr__set__contains__),
    __len__ = newmethod(descr__set__len__),
    __iter__ = newmethod(descr__set__iter__),
    copy = newmethod(descr_copy_fs),
    difference = newmethod(descr_difference_fs),
    intersection = newmethod(descr_intersection_fs),
    issubset = newmethod(descr_issubset),
    issuperset = newmethod(descr_issuperset),
    symmetric_difference = newmethod(descr_symmetric_difference_fs),
    union = newmethod(descr_union_fs),
    )
