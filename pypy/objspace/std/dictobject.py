"""
Reviewed 03-06-22
All common dictionary methods are correctly implemented,
tested, and complete. The only missing feature is support
for order comparisons.
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from stringobject import W_StringObject


class W_DictObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    def __init__(w_self, space, list_pairs_w):
        W_Object.__init__(w_self, space)
        w_self.data = [ [space.unwrap(space.hash(w_key)), w_key, w_value]
                        for w_key,w_value in list_pairs_w ]

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.data)

    def lookup(self, w_lookup, create=False):
        # this lookup is where most of the start-up time is consumed.
        # Hashing helps a lot.
        space = self.space
        lookup_hash = space.unwrap(space.hash(w_lookup))
        for cell in self.data:
            if (cell[0] == lookup_hash and
                space.is_true(space.eq(w_lookup, cell[1]))):
                break
        else:
            if not create:
                raise OperationError(space.w_KeyError, w_lookup)
            cell = [lookup_hash, w_lookup, None]
            self.data.append(cell)
        return cell

registerimplementation(W_DictObject)


def unwrap__Dict(space, w_dict):
    result = {}
    for hash, w_key, w_value in w_dict.data:
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
    return w_dict.lookup(w_lookup)[2]

def setitem__Dict_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    cell = w_dict.lookup(w_newkey, create=True)
    cell[2] = w_newvalue

def delitem__Dict_ANY(space, w_dict, w_lookup):
    cell = w_dict.lookup(w_lookup)
    # overwrite the cell with any other one removed from the dictionary
    cell[:] = w_dict.data.pop()

def len__Dict(space, w_dict):
    return space.wrap(len(w_dict.data))

def contains__Dict_ANY(space, w_dict, w_lookup):
    try:
        w_dict.lookup(w_lookup)
    except OperationError:
        # assert e.match(space, space.w_KeyError)
        return space.w_False
    else:
        return space.w_True

dict_has_key__Dict_ANY = contains__Dict_ANY

def iter__Dict(space, w_dict):
    import iterobject
    w_keys = dict_keys__Dict(space, w_dict)
    return iterobject.W_SeqIterObject(space, w_keys)
    
def eq__Dict_Dict(space, w_left, w_right):
    if space.is_true(space.is_(w_left, w_right)):
        return space.w_True

    dataleft = w_left.data
    dataright = w_right.data
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
    dataleft = w_left.data
    dataright = w_right.data
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
                                      for hash,w_key,w_value in w_self.data])

def dict_items__Dict(space, w_self):
    return space.newlist([ space.newtuple([w_key,w_value])
                           for hash,w_key,w_value in w_self.data ])

def dict_keys__Dict(space, w_self):
    return space.newlist([ w_key
                           for hash,w_key,w_value in w_self.data ])

def dict_values__Dict(space, w_self):
    return space.newlist([ w_value
                           for hash,w_key,w_value in w_self.data ])

def dict_clear__Dict(space, w_self):
    w_self.data = []

def dict_get__Dict_ANY_ANY(space, w_dict, w_lookup, w_default):
    try:
        return w_dict.lookup(w_lookup)[2]
    except OperationError:
        # assert e.match(space, space.w_KeyError)
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
