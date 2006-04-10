from pypy.objspace.std.objspace import W_Object, OperationError
from pypy.objspace.std.objspace import registerimplementation, register_all
from pypy.objspace.std.model import WITHSET
from pypy.objspace.std.stdtypedef import StdObjSpaceMultiMethod
from pypy.rpython.objectmodel import r_dict
from pypy.rpython.rarithmetic import intmask
from pypy.interpreter import gateway

class W_BaseSetObject(W_Object):

    def __init__(w_self, space, wrappeditems=None):
        W_Object.__init__(w_self, space)
        w_self.setdata = setdata = r_dict(space.eq_w, space.hash_w)
        if wrappeditems is not None:
            iterable_w = space.unpackiterable(wrappeditems)
            for w_item in iterable_w:
                w_self.setdata[w_item] = None

    def __repr__(w_self):
        """representation for debugging purposes"""
        reprlist = [repr(w_item) for w_item in w_self.setdata.keys()]
        return "<%s(%s)>" % (w_self.__class__.__name__, ', '.join(reprlist))

class W_SetObject(W_BaseSetObject):
    from pypy.objspace.std.settype import set_typedef as typedef

class W_FrozensetObject(W_BaseSetObject):
    from pypy.objspace.std.frozensettype import frozenset_typedef as typedef

    def __init__(w_self, space, wrappeditems):
        W_BaseSetObject.__init__(w_self, space, wrappeditems)
        w_self.hash = -1

registerimplementation(W_SetObject)
registerimplementation(W_FrozensetObject)

class W_SetIterObject(W_Object):
    from pypy.objspace.std.settype import setiter_typedef as typedef

    def __init__(w_self, space, setdata):
        W_Object.__init__(w_self, space)
        w_self.content = content = setdata
        w_self.len = len(content)
        w_self.pos = 0
        w_self.iterator = w_self.content.iterkeys()

    def next_entry(w_self):
        for w_key in w_self.iterator:
            return w_key
        else:
            return None

registerimplementation(W_SetIterObject)

def iter__SetIterObject(space, w_setiter):
    return w_setiter

def next__SetIterObject(space, w_setiter):
    content = w_setiter.content
    if content is not None:
        if w_setiter.len != len(content):
            w_setiter.len = -1   # Make this error state sticky
            raise OperationError(space.w_RuntimeError,
                     space.wrap("dictionary changed size during iteration"))
        # look for the next entry
        w_result = w_setiter.next_entry()
        if w_result is not None:
            w_setiter.pos += 1
            return w_result
        # no more entries
        w_setiter.content = None
    raise OperationError(space.w_StopIteration, space.w_None)

def len__SetIterObject(space, w_setiter):
    content = w_setiter.content
    if content is None or w_setiter.len == -1:
        return space.wrap(0)
    return space.wrap(w_setiter.len - w_setiter.pos)

# some helper functions

def _iter_to_dict(space, w_iterable):
    data = r_dict(space.eq_w, space.hash_w)
    iterable_w = space.unpackiterable(w_iterable)
    for w_item in iterable_w:
        data[w_item] = None

    return data

def _dict_to_set(space, rpdict):
    return space.newset(W_SetIterObject(space, rpdict))

def _dict_to_frozenset(space, rpdict):
    #return space.newfrozenset(space.newtuple(rpdict.keys()))
    return space.newfrozenset(W_SetIterObject(space, rpdict))

# helper functions for set operation on dicts

def _is_setlike(space, w_obj):
    if space.is_true(space.isinstance(w_obj, space.w_set)) or \
            space.is_true(space.isinstance(w_obj, space.w_frozenset)):
        return True
    else:
        return False

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
        ld[w_key] = None

    return ld, rdict

#end helper functions

def set_update__Set_ANY(space, w_left, w_other):
    """Update a set with the union of itself and another."""
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _union_dict(space, ld, rd, True)
    return space.w_None

def inplace_or__Set_Set(space, w_left, w_other):
    set_update__Set_ANY(space, w_left, w_other)
    return w_left

inplace_or__Set_Frozenset = inplace_or__Set_Set

def set_add__Set_ANY(space, w_left, w_other):
    """Add an element to a set.

    This has no effect if the element is already present.
    """
    w_left.setdata[w_other] = None
    return space.w_None

def set_copy__Set(space, w_left):
    return space.newset(w_left)

def frozenset_copy__Frozenset(space, w_left):
    return space.newfrozenset(w_left)

def set_clear__Set(space, w_left):
    w_left.setdata.clear()
    return space.w_None

def set_difference__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _difference_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

sub__Set_Set = set_difference__Set_ANY
sub__Set_Frozenset = set_difference__Set_ANY

def frozenset_difference__Frozenset_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _difference_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)

sub__Frozenset_Set = frozenset_difference__Frozenset_ANY
sub__Frozenset_Frozenset = frozenset_difference__Frozenset_ANY


def set_difference_update__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _difference_dict(space, ld, rd, True)
    return space.w_None

def inplace_sub__Set_Set(space, w_left, w_other):
    set_difference_update__Set_ANY(space, w_left, w_other)
    return w_left

inplace_sub__Set_Frozenset = inplace_sub__Set_Set

def eq__Set_ANY(space, w_left, w_other):
    if not _is_setlike(space, w_other):
        return space.w_False
    if space.is_w(w_left, w_other):
        return space.w_True

    if len(w_left.setdata) != len(w_other.setdata):
        return space.w_False

    for w_key in w_left.setdata.iterkeys():
        if w_key not in w_other.setdata:
            return space.w_False
    return space.w_True

eq__Frozenset_ANY = eq__Set_ANY

def contains__Set_ANY(space, w_left, w_other):
    try:
        r = w_other in w_left.setdata
        return space.newbool(r)
    except Exception, exp:
        if _is_setlike(space, w_other):
            w_f = space.newfrozenset(w_other)
            return space.newbool(w_f)
        else:
            return space.w_False

contains__Frozenset_ANY = contains__Set_ANY

def set_issubset__Set_Set(space, w_left, w_other):
    if space.is_w(w_left, w_other):
        return space.w_True

    ld, rd = w_left.setdata, w_other.setdata
    if len(ld) > len(rd):
        return space.w_False

    for w_key in ld:
        if w_key not in rd:
            return space.w_False
    return space.w_True

set_issubset__Set_Frozenset = set_issubset__Set_Set
frozenset_issubset__Frozenset_Set = set_issubset__Set_Set
frozenset_issubset__Frozenset_Frozenset = set_issubset__Set_Set

le__Set_Set = set_issubset__Set_Set
le__Set_Frozenset = set_issubset__Set_Set
le__Frozenset_Frozenset = set_issubset__Set_Set

def set_issuperset__Set_Set(space, w_left, w_other):
    if space.is_w(w_left, w_other):
        return space.w_True

    ld, rd = w_left.setdata, w_other.setdata
    if len(ld) < len(rd):
        return space.w_False

    for w_key in rd:
        if w_key not in ld:
            return space.w_False
    return space.w_True

set_issuperset__Set_Frozenset = set_issuperset__Set_Set
frozenset_issuperset__Frozenset_Set = set_issuperset__Set_Set
frozenset_issuperset__Frozenset_Frozenset = set_issuperset__Set_Set

ge__Set_Set = set_issuperset__Set_Set
ge__Set_Frozenset = set_issuperset__Set_Set
ge__Frozenset_Frozenset = set_issuperset__Set_Set

def set_discard__Set_ANY(space, w_left, w_item):
    if w_item in w_left.setdata:
        del w_left.setdata[w_item]
    
def set_remove__Set_ANY(space, w_left, w_item):
    try:
        del w_left.setdata[w_item]
    except KeyError:
        raise OperationError(space.w_KeyError,
                space.call_method(w_item,'__repr__'))

def hash__Set(space, w_set):
    raise OperationError(space.w_TypeError,
            space.wrap('set objects are unhashable'))

def hash__Frozenset(space, w_set):
    if w_set.hash != -1:
        return space.wrap(w_set.hash)
    hash = 1927868237
    hash *= (len(w_set.setdata) + 1)
    for w_item in w_set.setdata.iterkeys():
        h = space.int_w(space.hash(w_item))
        hash ^= (h ^ (h << 16) ^ 89869747)  * 3644798167
    hash = hash * 69069 + 907133923
    if hash == -1:
        hash = 590923713
    hash = intmask(hash)
    w_set.hash = hash

    return space.wrap(hash)

def set_pop__Set(space, w_left):
    if len(w_left.setdata) == 0:
        raise OperationError(space.w_KeyError,
                                space.wrap('pop from an empty set'))
    w_keys = w_left.setdata.keys()
    w_value = w_keys[0]
    del w_left.setdata[w_value]

    return w_value

def set_intersection__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _intersection_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

and__Set_Set = set_intersection__Set_ANY
and__Set_Frozenset = set_intersection__Set_ANY

def frozenset_intersection__Frozenset_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _intersection_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)

and__Frozenset_Set = frozenset_intersection__Frozenset_ANY
and__Frozenset_Frozenset = frozenset_intersection__Frozenset_ANY

def set_intersection_update__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _intersection_dict(space, ld, rd, True)
    return space.w_None

def inplace_and__Set_Set(space, w_left, w_other):
    set_intersection_update__Set_ANY(space, w_left, w_other)
    return w_left

inplace_and__Set_Frozenset = inplace_and__Set_Set

def set_symmetric_difference__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _symmetric_difference_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

xor__Set_Set = set_symmetric_difference__Set_ANY
xor__Set_Frozenset = set_symmetric_difference__Set_ANY

def frozenset_symmetric_difference__Frozenset_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _symmetric_difference_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)

xor__Frozenset_Set = frozenset_symmetric_difference__Frozenset_ANY
xor__Frozenset_Frozenset = frozenset_symmetric_difference__Frozenset_ANY

def set_symmetric_difference_update__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _symmetric_difference_dict(space, ld, rd, True)
    return space.w_None

def inplace_xor__Set_Set(space, w_left, w_other):
    set_symmetric_difference_update__Set_ANY(space, w_left, w_other)
    return w_left

inplace_xor__Set_Frozenset = inplace_xor__Set_Set

def set_union__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _union_dict(space, ld, rd, False)
    return _dict_to_set(space, new_ld)

or__Set_Set = set_union__Set_ANY
or__Set_Frozenset = set_union__Set_ANY

def frozenset_union__Frozenset_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, _iter_to_dict(space, w_other)
    new_ld, rd = _union_dict(space, ld, rd, False)
    return _dict_to_frozenset(space, new_ld)

or__Frozenset_Set = frozenset_union__Frozenset_ANY
or__Frozenset_Frozenset = frozenset_union__Frozenset_ANY

def len__Set(space, w_left):
    return space.newint(len(w_left.setdata))

len__Frozenset = len__Set

def iter__Set(space, w_left):
    return W_SetIterObject(space, w_left.setdata)

iter__Frozenset = iter__Set

def cmp__Set_Set(space, w_left, w_other):
    raise OperationError(space.w_TypeError,
            space.wrap('cannot compare sets using cmp()'))

cmp__Set_Frozenset = cmp__Set_Set
cmp__Frozenset_Frozenset = cmp__Set_Set
cmp__Frozenset_Set = cmp__Set_Set

def init__Set(space, w_set, __args__):
    w_iterable, = __args__.parse('set',
                            (['some_iterable'], None, None),
                            [W_SetObject(space,None)])
    W_SetObject.__init__(w_set, space, w_iterable)

app = gateway.applevel("""
    def ne__Set_ANY(s, o):
        return not s == o

    def gt__Set_Set(s, o):
        return s != o and s.issuperset(o)

    def lt__Set_Set(s, o):
        return s != o and s.issubset(o)

    def repr__Set(s):
        return 'set(%s)' % [x for x in s]

    def repr__Frozenset(s):
        return 'frozenset(%s)' % [x for x in s]

""", filename=__file__)

ne__Set_ANY = app.interphook("ne__Set_ANY")
ne__Frozenset_ANY = ne__Set_ANY

gt__Set_Set = app.interphook("gt__Set_Set")
gt__Set_Frozenset = gt__Set_Set
gt__Frozenset_Set = gt__Set_Set
gt__Frozenset_Frozenset = gt__Set_Set

lt__Set_Set = app.interphook("lt__Set_Set")
lt__Set_Frozenset = lt__Set_Set
lt__Frozenset_Set = lt__Set_Set
lt__Frozenset_Frozenset = lt__Set_Set

repr__Set = app.interphook('repr__Set')
repr__Frozenset = app.interphook('repr__Frozenset')

from pypy.objspace.std import frozensettype
from pypy.objspace.std import settype

# make sure that the 'register_all' function gets only the appropriate
# methods

sdg = [(n, m) for n, m in vars().items() if n.find('__Frozenset') == -1]
fdg = [(n, m) for n, m in vars().items() if n.find('__Set') == -1]

register_all(dict(sdg), settype)
register_all(dict(fdg), frozensettype)

# this doesn't work:
#register_all(vars(), frozensettype)
#register_all(vars(), settype)
