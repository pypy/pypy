from pypy.objspace.std.objspace import W_Object, OperationError
from pypy.objspace.std.objspace import registerimplementation, register_all
from pypy.rlib.objectmodel import r_dict
from pypy.rlib.rarithmetic import intmask, r_uint
from pypy.interpreter import gateway
from pypy.interpreter.argument import Signature
from pypy.objspace.std.settype import set_typedef as settypedef
from pypy.objspace.std.frozensettype import frozenset_typedef as frozensettypedef

class W_BaseSetObject(W_Object):
    typedef = None

    # make sure that Base is used for Set and Frozenset in multimethod
    # declarations
    @classmethod
    def is_implementation_for(cls, typedef): 
        if typedef is frozensettypedef or typedef is settypedef:
            assert cls is W_BaseSetObject
            return True
        return False


    def __init__(w_self, space, setdata=None):
        if setdata is None:
            w_self.setdata = r_dict(space.eq_w, space.hash_w)
        else:
            w_self.setdata = setdata.copy()

    def __repr__(w_self):
        """representation for debugging purposes"""
        reprlist = [repr(w_item) for w_item in w_self.setdata.keys()]
        return "<%s(%s)>" % (w_self.__class__.__name__, ', '.join(reprlist))

    def _newobj(w_self, space, rdict_w=None):
        #return space.call(space.type(w_self),W_SetIterObject(rdict_w))
        objtype = type(w_self)
        if objtype is W_SetObject:
            obj = W_SetObject(space, rdict_w)
        elif objtype is W_FrozensetObject:
            obj = W_FrozensetObject(space, rdict_w)
        else:
            itemiterator = space.iter(W_SetIterObject(rdict_w))
            obj = space.call_function(space.type(w_self),itemiterator)
        return obj

    _lifeline_ = None
    def getweakref(self):
        return self._lifeline_
    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline

class W_SetObject(W_BaseSetObject):
    from pypy.objspace.std.settype import set_typedef as typedef

class W_FrozensetObject(W_BaseSetObject):
    from pypy.objspace.std.frozensettype import frozenset_typedef as typedef

    def __init__(w_self, space, setdata):
        W_BaseSetObject.__init__(w_self, space, setdata)
        w_self.hash = -1

registerimplementation(W_BaseSetObject)
registerimplementation(W_SetObject)
registerimplementation(W_FrozensetObject)

class W_SetIterObject(W_Object):
    from pypy.objspace.std.settype import setiter_typedef as typedef

    def __init__(w_self, setdata):
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
                     space.wrap("Set changed size during iteration"))
        # look for the next entry
        w_result = w_setiter.next_entry()
        if w_result is not None:
            w_setiter.pos += 1
            return w_result
        # no more entries
        w_setiter.content = None
    raise OperationError(space.w_StopIteration, space.w_None)

# XXX __length_hint__()
##def len__SetIterObject(space, w_setiter):
##    content = w_setiter.content
##    if content is None or w_setiter.len == -1:
##        return space.wrap(0)
##    return space.wrap(w_setiter.len - w_setiter.pos)

# some helper functions

def make_setdata_from_w_iterable(space, w_iterable=None):
    data = r_dict(space.eq_w, space.hash_w)
    if w_iterable is not None:
        for w_item in space.listview(w_iterable):
            data[w_item] = None
    return data

def _initialize_set(space, w_obj, w_iterable=None):
    w_obj.setdata.clear()
    if w_iterable is not None:
        w_obj.setdata.update(make_setdata_from_w_iterable(space, w_iterable))

def _convert_set_to_frozenset(space, w_obj):
    if space.is_true(space.isinstance(w_obj, space.w_set)):
        return W_FrozensetObject(space,
                                 make_setdata_from_w_iterable(space, w_obj))
    else:
        return None

# helper functions for set operation on dicts

def _is_frozenset_exact(w_obj):
    if (w_obj is not None) and (type(w_obj) is W_FrozensetObject):
        return True
    else:
        return False

def _is_eq(ld, rd):
    if len(ld) != len(rd):
        return False
    for w_key in ld:
        if w_key not in rd:
            return False
    return True

def _union_dict(ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    ld.update(rdict)
    return ld, rdict

def _difference_dict(ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    del_list_w = []
    for w_key in ld:
        if w_key in rdict:
            del_list_w.append(w_key)
    for w_key in del_list_w:
        del ld[w_key]

    return ld, rdict

def _intersection_dict(ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    del_list_w = []
    for w_key in ld:
        if w_key not in rdict:
            del_list_w.append(w_key)

    for w_key in del_list_w:
        del ld[w_key]

    return ld, rdict


def _symmetric_difference_dict(ldict, rdict, isupdate):
    if isupdate:
        ld = ldict
    else:
        ld = ldict.copy()
    del_list_w = []
    add_list_w = []
    for w_key in ld:
        if w_key in rdict:
            del_list_w.append(w_key)

    for w_key in rdict:
        if w_key not in ld:
            add_list_w.append(w_key)

    for w_key in del_list_w:
        del ld[w_key]

    for w_key in add_list_w:
        ld[w_key] = None

    return ld, rdict

def _issubset_dict(ldict, rdict):
    if len(ldict) > len(rdict):
        return False

    for w_key in ldict:
        if w_key not in rdict:
            return False
    return True


#end helper functions

def set_update__Set_BaseSet(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _union_dict(ld, rd, True)
    return space.w_None

def set_update__Set_ANY(space, w_left, w_other):
    """Update a set with the union of itself and another."""
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _union_dict(ld, rd, True)
    return space.w_None

def inplace_or__Set_Set(space, w_left, w_other):
    set_update__Set_BaseSet(space, w_left, w_other)
    return w_left

inplace_or__Set_Frozenset = inplace_or__Set_Set

def set_add__Set_ANY(space, w_left, w_other):
    """Add an element to a set.

    This has no effect if the element is already present.
    """
    w_left.setdata[w_other] = None
    return space.w_None

def set_copy__Set(space, w_set):
    return w_set._newobj(space,w_set.setdata)

def frozenset_copy__Frozenset(space, w_left):
    if _is_frozenset_exact(w_left):
        return w_left
    else:
        return set_copy__Set(space,w_left)

def set_clear__Set(space, w_left):
    w_left.setdata.clear()
    return space.w_None

def set_difference__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _difference_dict(ld, rd, False)
    return w_left._newobj(space, new_ld)

set_difference__Set_Frozenset = set_difference__Set_Set
frozenset_difference__Frozenset_Set = set_difference__Set_Set
frozenset_difference__Frozenset_Frozenset = set_difference__Set_Set
sub__Set_Set = set_difference__Set_Set
sub__Set_Frozenset = set_difference__Set_Set
sub__Frozenset_Set = set_difference__Set_Set
sub__Frozenset_Frozenset = set_difference__Set_Set

def set_difference__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _difference_dict(ld, rd, False)
    return w_left._newobj(space, new_ld)

frozenset_difference__Frozenset_ANY = set_difference__Set_ANY


def set_difference_update__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _difference_dict(ld, rd, True)
    return space.w_None

set_difference_update__Set_Frozenset = set_difference_update__Set_Set

def set_difference_update__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _difference_dict(ld, rd, True)
    return space.w_None

def inplace_sub__Set_Set(space, w_left, w_other):
    set_difference_update__Set_Set(space, w_left, w_other)
    return w_left

inplace_sub__Set_Frozenset = inplace_sub__Set_Set

def eq__Set_Set(space, w_left, w_other):
    # optimization only (the general case is eq__Set_settypedef)
    return space.wrap(_is_eq(w_left.setdata, w_other.setdata))

eq__Set_Frozenset = eq__Set_Set
eq__Frozenset_Frozenset = eq__Set_Set
eq__Frozenset_Set = eq__Set_Set

def eq__Set_settypedef(space, w_left, w_other):
    rd = make_setdata_from_w_iterable(space, w_other)
    return space.wrap(_is_eq(w_left.setdata, rd))

eq__Set_frozensettypedef = eq__Set_settypedef
eq__Frozenset_settypedef = eq__Set_settypedef
eq__Frozenset_frozensettypedef = eq__Set_settypedef

def eq__Set_ANY(space, w_left, w_other):
    # workaround to have "set() == 42" return False instead of falling
    # back to cmp(set(), 42) because the latter raises a TypeError
    return space.w_False

eq__Frozenset_ANY = eq__Set_ANY

def ne__Set_Set(space, w_left, w_other):
    return space.wrap(not _is_eq(w_left.setdata, w_other.setdata))

ne__Set_Frozenset = ne__Set_Set
ne__Frozenset_Frozenset = ne__Set_Set
ne__Frozenset_Set = ne__Set_Set

def ne__Set_settypedef(space, w_left, w_other):
    rd = make_setdata_from_w_iterable(space, w_other)
    return space.wrap(_is_eq(w_left.setdata, rd))

ne__Set_frozensettypedef = ne__Set_settypedef
ne__Frozenset_settypedef = ne__Set_settypedef
ne__Frozenset_frozensettypedef = ne__Set_settypedef


def ne__Set_ANY(space, w_left, w_other):
    # more workarounds
    return space.w_True

ne__Frozenset_ANY = ne__Set_ANY

def contains__Set_ANY(space, w_left, w_other):
    try:
        return space.newbool(w_other in w_left.setdata)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            w_f = _convert_set_to_frozenset(space, w_other)
            if w_f is not None:
                return space.newbool(w_f in w_left.setdata)
        raise

contains__Frozenset_ANY = contains__Set_ANY

def set_issubset__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    if space.is_w(w_left, w_other):
        return space.w_True
    ld, rd = w_left.setdata, w_other.setdata
    return space.wrap(_issubset_dict(ld, rd))

set_issubset__Set_Frozenset = set_issubset__Set_Set
frozenset_issubset__Frozenset_Set = set_issubset__Set_Set
frozenset_issubset__Frozenset_Frozenset = set_issubset__Set_Set

def set_issubset__Set_ANY(space, w_left, w_other):
    if space.is_w(w_left, w_other):
        return space.w_True

    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    return space.wrap(_issubset_dict(ld, rd))

frozenset_issubset__Frozenset_ANY = set_issubset__Set_ANY

le__Set_Set = set_issubset__Set_Set
le__Set_Frozenset = set_issubset__Set_Set
le__Frozenset_Set = set_issubset__Set_Set
le__Frozenset_Frozenset = set_issubset__Set_Set

def set_issuperset__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    if space.is_w(w_left, w_other):
        return space.w_True

    ld, rd = w_left.setdata, w_other.setdata
    return space.wrap(_issubset_dict(rd, ld))

set_issuperset__Set_Frozenset = set_issuperset__Set_Set
set_issuperset__Frozenset_Set = set_issuperset__Set_Set
set_issuperset__Frozenset_Frozenset = set_issuperset__Set_Set

def set_issuperset__Set_ANY(space, w_left, w_other):
    if space.is_w(w_left, w_other):
        return space.w_True

    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    return space.wrap(_issubset_dict(rd, ld))

frozenset_issuperset__Frozenset_ANY = set_issuperset__Set_ANY

ge__Set_Set = set_issuperset__Set_Set
ge__Set_Frozenset = set_issuperset__Set_Set
ge__Frozenset_Set = set_issuperset__Set_Set
ge__Frozenset_Frozenset = set_issuperset__Set_Set

# automatic registration of "lt(x, y)" as "not ge(y, x)" would not give the
# correct answer here!
def lt__Set_Set(space, w_left, w_other):
    if _is_eq(w_left.setdata, w_other.setdata):
        return space.w_False
    else:
        return le__Set_Set(space, w_left, w_other)

lt__Set_Frozenset = lt__Set_Set
lt__Frozenset_Set = lt__Set_Set
lt__Frozenset_Frozenset = lt__Set_Set

def gt__Set_Set(space, w_left, w_other):
    if _is_eq(w_left.setdata, w_other.setdata):
        return space.w_False
    else:
        return ge__Set_Set(space, w_left, w_other)

gt__Set_Frozenset = gt__Set_Set
gt__Frozenset_Set = gt__Set_Set
gt__Frozenset_Frozenset = gt__Set_Set

def _discard_from_set(space, w_left, w_item):
    """
    Discard an element from a set, with automatic conversion to
    frozenset if the argument is a set.

    Returns None if successfully removed, otherwise the object that
    wasn't there is returned.
    """
    try:
        del w_left.setdata[w_item]
        return None
    except KeyError:
        return w_item
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        w_f = _convert_set_to_frozenset(space, w_item)
        if w_f is None:
            raise
        
    try:
        del w_left.setdata[w_f]
        return None
    except KeyError:
        return w_f
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        return w_f
    
def set_discard__Set_ANY(space, w_left, w_item):
    _discard_from_set(space, w_left, w_item)

def set_remove__Set_ANY(space, w_left, w_item):
    w_f = _discard_from_set(space, w_left, w_item)
    if w_f is not None:
        space.raise_key_error(w_f)

def hash__Frozenset(space, w_set):
    multi = r_uint(1822399083) + r_uint(1822399083) + 1
    if w_set.hash != -1:
        return space.wrap(w_set.hash)
    hash = 1927868237
    hash *= (len(w_set.setdata) + 1)
    for w_item in w_set.setdata:
        h = space.hash_w(w_item)
        value = ((h ^ (h << 16) ^ 89869747)  * multi)
        hash = intmask(hash ^ value)
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

def set_intersection__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _intersection_dict(ld, rd, False)
    return w_left._newobj(space,new_ld)

set_intersection__Set_Frozenset = set_intersection__Set_Set
set_intersection__Frozenset_Frozenset = set_intersection__Set_Set
set_intersection__Frozenset_Set = set_intersection__Set_Set

def set_intersection__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _intersection_dict(ld, rd, False)
    return w_left._newobj(space,new_ld)

frozenset_intersection__Frozenset_ANY = set_intersection__Set_ANY

and__Set_Set = set_intersection__Set_Set
and__Set_Frozenset = set_intersection__Set_Set
and__Frozenset_Set = set_intersection__Set_Set
and__Frozenset_Frozenset = set_intersection__Set_Set

def set_intersection_update__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _intersection_dict(ld, rd, True)
    return space.w_None

set_intersection_update__Set_Frozenset = set_intersection_update__Set_Set

def set_intersection_update__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _intersection_dict(ld, rd, True)
    return space.w_None

def inplace_and__Set_Set(space, w_left, w_other):
    set_intersection_update__Set_Set(space, w_left, w_other)
    return w_left

inplace_and__Set_Frozenset = inplace_and__Set_Set

def set_symmetric_difference__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _symmetric_difference_dict(ld, rd, False)
    return w_left._newobj(space, new_ld)

set_symmetric_difference__Set_Frozenset = set_symmetric_difference__Set_Set
set_symmetric_difference__Frozenset_Set = set_symmetric_difference__Set_Set
set_symmetric_difference__Frozenset_Frozenset = \
                                        set_symmetric_difference__Set_Set

xor__Set_Set = set_symmetric_difference__Set_Set
xor__Set_Frozenset = set_symmetric_difference__Set_Set
xor__Frozenset_Set = set_symmetric_difference__Set_Set
xor__Frozenset_Frozenset = set_symmetric_difference__Set_Set


def set_symmetric_difference__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _symmetric_difference_dict(ld, rd, False)
    return w_left._newobj(space, new_ld)

frozenset_symmetric_difference__Frozenset_ANY = \
        set_symmetric_difference__Set_ANY

def set_symmetric_difference_update__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _symmetric_difference_dict(ld, rd, True)
    return space.w_None

set_symmetric_difference_update__Set_Frozenset = \
                                    set_symmetric_difference_update__Set_Set

def set_symmetric_difference_update__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _symmetric_difference_dict(ld, rd, True)
    return space.w_None

def inplace_xor__Set_Set(space, w_left, w_other):
    set_symmetric_difference_update__Set_Set(space, w_left, w_other)
    return w_left

inplace_xor__Set_Frozenset = inplace_xor__Set_Set

def set_union__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    ld, rd = w_left.setdata, w_other.setdata
    new_ld, rd = _union_dict(ld, rd, False)
    return w_left._newobj(space, new_ld)

set_union__Set_Frozenset = set_union__Set_Set
set_union__Frozenset_Set = set_union__Set_Set
set_union__Frozenset_Frozenset = set_union__Set_Set
or__Set_Set = set_union__Set_Set
or__Set_Frozenset = set_union__Set_Set
or__Frozenset_Set = set_union__Set_Set
or__Frozenset_Frozenset = set_union__Set_Set


def set_union__Set_ANY(space, w_left, w_other):
    ld, rd = w_left.setdata, make_setdata_from_w_iterable(space, w_other)
    new_ld, rd = _union_dict(ld, rd, False)
    return w_left._newobj(space, new_ld)

frozenset_union__Frozenset_ANY = set_union__Set_ANY

def len__Set(space, w_left):
    return space.newint(len(w_left.setdata))

len__Frozenset = len__Set

def iter__Set(space, w_left):
    return W_SetIterObject(w_left.setdata)

iter__Frozenset = iter__Set

def cmp__Set_settypedef(space, w_left, w_other):
    # hack hack until we get the expected result
    raise OperationError(space.w_TypeError,
            space.wrap('cannot compare sets using cmp()'))

cmp__Set_frozensettypedef = cmp__Set_settypedef
cmp__Frozenset_settypedef = cmp__Set_settypedef
cmp__Frozenset_frozensettypedef = cmp__Set_settypedef

init_signature = Signature(['some_iterable'], None, None)
init_defaults = [None]
def init__Set(space, w_set, __args__):
    w_iterable, = __args__.parse_obj(
            None, 'set',
            init_signature,
            init_defaults)
    _initialize_set(space, w_set, w_iterable)

def init__Frozenset(space, w_set, __args__):
    w_iterable, = __args__.parse_obj(
            None, 'set',
            init_signature,
            init_defaults)
    if w_set.hash == -1:
        _initialize_set(space, w_set, w_iterable)
        hash__Frozenset(space, w_set)

app = gateway.applevel("""
    def setrepr(currently_in_repr, s):
        'The app-level part of repr().'
        set_id = id(s)
        if set_id in currently_in_repr:
            return '%s(...)' % (s.__class__.__name__,)
        currently_in_repr[set_id] = 1
        try:
            return '%s(%s)' % (s.__class__.__name__, [x for x in s])
        finally:
            try:
                del currently_in_repr[set_id]
            except:
                pass
""", filename=__file__) 

setrepr = app.interphook("setrepr")

def repr__Set(space, w_set):
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return setrepr(space, w_currently_in_repr, w_set)

repr__Frozenset = repr__Set

app = gateway.applevel("""
    def reduce__Set(s):
        dict = getattr(s,'__dict__', None)
        return (s.__class__, (tuple(s),), dict)

""", filename=__file__)

set_reduce__Set = app.interphook('reduce__Set')
frozenset_reduce__Frozenset = app.interphook('reduce__Set')

from pypy.objspace.std import frozensettype
from pypy.objspace.std import settype

register_all(vars(), settype, frozensettype)
