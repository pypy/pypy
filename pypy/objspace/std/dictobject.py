"""
Reviewed 03-06-22
All common dictionary methods are correctly implemented,
tested, and complete. The only missing feature is support
for order comparisons.
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway

from pypy.objspace.std.restricted_int import r_uint

dummy = object()

class W_DictObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    def __init__(w_self, space, list_pairs_w):
        W_Object.__init__(w_self, space)
        
        w_self.used = 0
        w_self.data = []
        w_self.resize(len(list_pairs_w)*2)
        for w_k, w_v in list_pairs_w:
            w_self.insert(w_self.hash(w_k), w_k, w_v)
        
    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.data)

    def hash(w_self, w_obj):
        space = w_self.space
        return r_uint(space.unwrap(space.hash(w_obj)))

    def insert(self, h, w_key, w_value):
        cell = self.lookdict(h, w_key)
        if cell[2] is None:
            self.used += 1
            cell[:] = [h, w_key, w_value]
        else:
            cell[2] = w_value

    def resize(self, minused):
        newsize = 4
        while newsize < minused:
            newsize *= 2
        od = self.data

        self.used = 0
        self.data = [[r_uint(0), None, None] for i in range(newsize)]
        for h, k, v in od:
            if v is not None:
                self.insert(h, k, v)

    def non_empties(self):
        return [(h, w_k, w_v) for (h, w_k, w_v) in self.data if w_v is not None]
        
    def lookdict(self, lookup_hash, w_lookup):
        assert isinstance(lookup_hash, r_uint)
        space = self.space
        i = lookup_hash % len(self.data)

        entry = self.data[i]
        if entry[1] is None or \
           space.is_true(space.is_(w_lookup, entry[1])):
            return entry
        if entry[1] is dummy:
            freeslot = entry
        else:
            if entry[0] == lookup_hash and space.is_true(
                space.eq(entry[1], w_lookup)):
                return entry
            freeslot = None

        perturb = lookup_hash
        ##c = len(self.data) + 99
        while 1:
            ##c -= 1
            ##if not c:
            ##    import sys, pdb
            ##    print >> sys.stderr, 'dict lookup lost in infinite loop'
            ##    pdb.set_trace()
            i = (i << 2) + i + perturb + 1
            entry = self.data[i%len(self.data)]
            if entry[1] is None:
                if freeslot:
                    return freeslot
                else:
                    return entry
            if entry[0] == lookup_hash and entry[1] is not dummy \
                   and space.is_true(
                space.eq(entry[1], w_lookup)):
                return entry
            if entry[1] is dummy and freeslot is None:
                freeslot = entry
            perturb >>= 5

registerimplementation(W_DictObject)


def unwrap__Dict(space, w_dict):
    result = {}
    for hash, w_key, w_value in w_dict.non_empties():
        result[space.unwrap(w_key)] = space.unwrap(w_value)
    return result

def init__Dict(space, w_dict, w_args, w_kwds):
    dict_clear__Dict(space, w_dict)
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        pass
    elif len(args) == 1:
        # XXX do dict({...}) with dict_update__Dict_Dict()
        list_of_w_pairs = space.unpackiterable(args[0])
        for w_pair in list_of_w_pairs:
            pair = space.unpackiterable(w_pair)
            if len(pair)!=2:
                raise OperationError(space.w_ValueError,
                             space.wrap("dict() takes a sequence of pairs"))
            w_k, w_v = pair
            setitem__Dict_ANY_ANY(space, w_dict, w_k, w_v)
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("dict() takes at most 1 argument"))
    space.call_method(w_dict, 'update', w_kwds)

def getitem__Dict_ANY(space, w_dict, w_lookup):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    if entry[2] is not None:
        return entry[2]
    else:
        raise OperationError(space.w_KeyError, w_lookup)

def setitem__Dict_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    w_dict.insert(w_dict.hash(w_newkey), w_newkey, w_newvalue)
    if 2*w_dict.used > len(w_dict.data):
        w_dict.resize(2*w_dict.used)

def delitem__Dict_ANY(space, w_dict, w_lookup):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    if entry[2] is not None:
        w_dict.used -= 1
        entry[1] = dummy
        entry[2] = None
    else:
        raise OperationError(space.w_KeyError, w_lookup)
    
def len__Dict(space, w_dict):
    return space.wrap(w_dict.used)

def contains__Dict_ANY(space, w_dict, w_lookup):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    return space.newbool(entry[2] is not None)

dict_has_key__Dict_ANY = contains__Dict_ANY

def iter__Dict(space, w_dict):
    from pypy.objspace.std import iterobject
    w_keys = dict_keys__Dict(space, w_dict)
    return iterobject.W_SeqIterObject(space, w_keys)
    
def eq__Dict_Dict(space, w_left, w_right):
    if space.is_true(space.is_(w_left, w_right)):
        return space.w_True

    dataleft = w_left.non_empties()
    dataright = w_right.non_empties()
    if len(dataleft) != len(dataright):
        return space.w_False
    for hash, w_key, w_value in dataleft:
        try:
            w_rightval = space.getitem(w_right, w_key)
        except OperationError:
            return space.w_False
        if not space.is_true(space.eq(w_value, w_rightval)):
            return space.w_False
    return space.w_True
        
def lt__Dict_Dict(space, w_left, w_right):
    # Different sizes, no problem
    dataleft = w_left.non_empties()
    dataright = w_right.non_empties()
    if len(dataleft) < len(dataright):
        return space.w_True
    if len(dataleft) > len(dataright):
        return space.w_False

    # Same size
    for hash, w_key, w_value in dataleft:
        # This is incorrect, but we need to decide what comparisons on
        # dictionaries of equal size actually means
        # The Python language specification is silent on the subject
        try:
            w_rightval = space.getitem(w_right, w_key)
        except OperationError:
            return space.w_True
        if space.is_true(space.lt(w_value, w_rightval)):
            return space.w_True
    # The dictionaries are equal. This is correct.
    return space.w_False

def hash__Dict(space,w_dict):
    raise OperationError(space.w_TypeError,space.wrap("dict objects are unhashable"))

def dict_copy__Dict(space, w_self):
    return W_DictObject(space, [(w_key,w_value)
                                for hash,w_key,w_value in w_self.data
                                if w_value is not None])

def dict_items__Dict(space, w_self):
    return space.newlist([ space.newtuple([w_key,w_value])
                           for hash,w_key,w_value in w_self.data 
                           if w_value is not None])

def dict_keys__Dict(space, w_self):
    return space.newlist([ w_key
                           for hash,w_key,w_value in w_self.data
                           if w_value is not None])

def dict_values__Dict(space, w_self):
    return space.newlist([ w_value
                           for hash,w_key,w_value in w_self.data 
                           if w_value is not None])

def dict_clear__Dict(space, w_self):
    w_self.data = [[0, None, None]]
    w_self.used = 0

def dict_get__Dict_ANY_ANY(space, w_dict, w_lookup, w_default):
    entry = w_dict.lookdict(w_dict.hash(w_lookup), w_lookup)
    if entry[2] is not None:
        return entry[2]
    else:
        return w_default

# Now we only handle one implementation of dicts, this one.
# The fix is to move this to dicttype.py, and do a
# multimethod lookup mapping str to StdObjSpace.str
# This cannot happen until multimethods are fixed. See dicttype.py
def app_str__Dict(d):
    items = []
    for k, v in d.iteritems():
        items.append("%r: %r" % (k, v))
    return "{%s}" % ', '.join(items)

repr__Dict = str__Dict = gateway.app2interp(app_str__Dict)
from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
