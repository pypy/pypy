"""
Reviewed 03-06-22
All common dictionary methods are correctly implemented,
tested, and complete. The only missing feature is support
for order comparisons.
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway

from pypy.rpython.rarithmetic import r_uint

class Entry:
    def __init__(self):
        self.hash = r_uint(0)
        self.w_key = None
        self.w_value = None
    def __repr__(self):
        return '<Entry %r,%r,%r>'%(self.hash, self.w_key, self.w_value)

class W_DictObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    def __init__(w_self, space, list_pairs_w):
        W_Object.__init__(w_self, space)
        
        w_self.used = 0
        w_self.data = []
        w_self.resize(len(list_pairs_w)*2)
        w_self.w_dummy = space.newlist([])
        for w_k, w_v in list_pairs_w:
            w_self.insert(w_self.hash(w_k), w_k, w_v)
        
    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.data)

    def hash(w_self, w_obj):
        space = w_self.space
        return r_uint(space.int_w(space.hash(w_obj)))

    def insert(self, h, w_key, w_value):
        entry = self.lookdict(h, w_key)
        if entry.w_value is None:
            self.used += 1
            entry.hash = h
            entry.w_key = w_key
            entry.w_value = w_value
        else:
            entry.w_value = w_value

    def resize(self, minused):
        newsize = 4
        while newsize < minused:
            newsize *= 2
        od = self.data

        self.used = 0
        self.data = [Entry() for i in range(newsize)]
        for entry in od:
            if entry.w_value is not None:
                self.insert(entry.hash, entry.w_key, entry.w_value)

    def lookdict(self, lookup_hash, w_lookup):
        assert isinstance(lookup_hash, r_uint)
        space = self.space
        i = lookup_hash % len(self.data)

        entry = self.data[i]
        if entry.w_key is None or space.is_w(w_lookup, entry.w_key):
            return entry
        if entry.w_key is self.w_dummy:
            freeslot = entry
        else:
            if entry.hash == lookup_hash and space.eq_w(entry.w_key, w_lookup):
                return entry
            freeslot = None

        perturb = lookup_hash
        while 1:
            i = (i << 2) + i + perturb + 1
            entry = self.data[i%len(self.data)]
            if entry.w_key is None:
                if freeslot:
                    return freeslot
                else:
                    return entry
            if entry.hash == lookup_hash and entry.w_key is not self.w_dummy \
                   and space.eq_w(entry.w_key, w_lookup):
                return entry
            if entry.w_key is self.w_dummy and freeslot is None:
                freeslot = entry
            perturb >>= 5

    def unwrap(w_dict):
        space = w_dict.space
        result = {}
        for entry in w_dict.data:
            if entry.w_value is not None:
                # XXX generic mixed types unwrap
                result[space.unwrap(entry.w_key)] = space.unwrap(entry.w_value)
        return result

registerimplementation(W_DictObject)


def init__Dict(space, w_dict, __args__):
    w_src, w_kwds = __args__.parse('dict',
                          (['seq_or_map'], None, 'kwargs'), # signature
                          [W_DictObject(space, [])])        # default argument
    dict_clear__Dict(space, w_dict)
    # XXX do dict({...}) with dict_update__Dict_Dict()
    try:
        space.getattr(w_src, space.wrap("keys"))
    except OperationError:
        list_of_w_pairs = space.unpackiterable(w_src)
        for w_pair in list_of_w_pairs:
            pair = space.unpackiterable(w_pair)
            if len(pair)!=2:
                raise OperationError(space.w_ValueError,
                             space.wrap("dict() takes a sequence of pairs"))
            w_k, w_v = pair
            setitem__Dict_ANY_ANY(space, w_dict, w_k, w_v)
    else:
        if space.is_true(w_src):
            from pypy.objspace.std.dicttype import dict_update__ANY_ANY
            dict_update__ANY_ANY(space, w_dict, w_src)
    if space.is_true(w_kwds):
        space.call_method(w_dict, 'update', w_kwds)

def getitem__Dict_ANY(space, w_dict, w_lookup):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    if entry.w_value is not None:
        return entry.w_value
    else:
        raise OperationError(space.w_KeyError, w_lookup)

def setitem__Dict_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    w_dict.insert(w_dict.hash(w_newkey), w_newkey, w_newvalue)
    if 2*w_dict.used > len(w_dict.data):
        w_dict.resize(2*w_dict.used)

def delitem__Dict_ANY(space, w_dict, w_lookup):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    if entry.w_value is not None:
        w_dict.used -= 1
        entry.w_key = w_dict.w_dummy
        entry.w_value = None
    else:
        raise OperationError(space.w_KeyError, w_lookup)
    
def len__Dict(space, w_dict):
    return space.wrap(w_dict.used)

def contains__Dict_ANY(space, w_dict, w_lookup):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    return space.newbool(entry.w_value is not None)

dict_has_key__Dict_ANY = contains__Dict_ANY

def iter__Dict(space, w_dict):
    from pypy.objspace.std import iterobject
    w_keys = dict_keys__Dict(space, w_dict)
    return iterobject.W_SeqIterObject(space, w_keys)
    
def eq__Dict_Dict(space, w_left, w_right):
    if space.is_true(space.is_(w_left, w_right)):
        return space.w_True

    if w_left.used != w_right.used:
        return space.w_False
    for entry in w_left.data:
        w_val = entry.w_value
        if w_val is None:
            continue
        rightentry = w_right.lookdict(entry.hash, entry.w_key)
        if rightentry.w_value is None:
            return space.w_False
        if not space.eq_w(w_val, rightentry.w_value):
            return space.w_False
    return space.w_True

def characterize(space, adata, w_b):
    """ (similar to CPython) 
    returns the smallest key in adata for which b's value is different or absent and this value """
    w_smallest_diff_a_key = None
    w_its_value = None
    for entry in adata:
        w_val = entry.w_value
        if w_val is None:
            continue
        w_key = entry.w_key
        if w_smallest_diff_a_key is None or space.is_true(space.lt(w_key, w_smallest_diff_a_key)):
            b_entry = w_b.lookdict(entry.hash, w_key)
            if b_entry.w_value is None:
                w_its_value = w_val
                w_smallest_diff_a_key = w_key
            else:
                if not space.eq_w(w_val, b_entry.w_value):
                    w_its_value = w_val
                    w_smallest_diff_a_key = w_key
    return w_smallest_diff_a_key, w_its_value

def lt__Dict_Dict(space, w_left, w_right):
    # Different sizes, no problem
    if w_left.used < w_right.used:
        return space.w_True
    if w_left.used > w_right.used:
        return space.w_False

    # Same size
    w_leftdiff, w_leftval = characterize(space, w_left.data, w_right)
    if w_leftdiff is None:
        return space.w_False
    w_rightdiff, w_rightval = characterize(space, w_right.data, w_left)
    w_res = space.w_False
    if w_rightdiff is not None:
        w_res = space.lt(w_leftdiff, w_rightdiff)
    if space.is_w(w_res, space.w_False) and space.eq_w(w_leftdiff, w_rightdiff) and w_rightval is not None:
        w_res = space.lt(w_leftval, w_rightval)
    return w_res


def hash__Dict(space,w_dict):
    raise OperationError(space.w_TypeError,space.wrap("dict objects are unhashable"))

def dict_copy__Dict(space, w_self):
    return W_DictObject(space, [(entry.w_key,entry.w_value)
                                for entry in w_self.data
                                if entry.w_value is not None])

def dict_items__Dict(space, w_self):
    return space.newlist([ space.newtuple([entry.w_key,entry.w_value])
                           for entry in w_self.data
                           if entry.w_value is not None])

def dict_keys__Dict(space, w_self):
    return space.newlist([ entry.w_key
                           for entry in w_self.data
                           if entry.w_value is not None])

def dict_values__Dict(space, w_self):
    return space.newlist([ entry.w_value
                           for entry in w_self.data
                           if entry.w_value is not None])

def dict_clear__Dict(space, w_self):
    w_self.data = [Entry()]
    w_self.used = 0

def dict_get__Dict_ANY_ANY(space, w_dict, w_lookup, w_default):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    if entry.w_value is not None:
        return entry.w_value
    else:
        return w_default

app = gateway.applevel('''
    def dictstr(currently_in_repr, d):
        # Now we only handle one implementation of dicts, this one.
        # The fix is to move this to dicttype.py, and do a
        # multimethod lookup mapping str to StdObjSpace.str
        # This cannot happen until multimethods are fixed. See dicttype.py
            dict_id = id(d)
            if dict_id in currently_in_repr:
                return '{...}'
            currently_in_repr[dict_id] = 1
            try:
                items = []
                for k, v in d.iteritems():
                    items.append(repr(k) + ": " + repr(v))
                return "{" +  ', '.join(items) + "}"
            finally:
                try:
                    del currently_in_repr[dict_id]
                except:
                    pass
''', filename=__file__)

dictstr = app.interphook("dictstr")

def str__Dict(space, w_dict):
    if w_dict.used == 0:
        return space.wrap('{}')
    statedict = space.get_ec_state_dict()
    w_currently_in_repr = space.getexecutioncontext()._py_repr
    return dictstr(space, w_currently_in_repr, w_dict)

repr__Dict = str__Dict

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
