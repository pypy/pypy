"""
Reviewed 03-06-22
All common dictionary methods are correctly implemented,
tested, and complete. The only missing feature is support
for order comparisons.
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from dicttype import W_DictType
from stringobject import W_StringObject

class _NoValueInCell: pass

class Cell:
    def __init__(self,w_value=_NoValueInCell):
        self.w_value = w_value

    def get(self):
        if self.is_empty():
            raise ValueError, "get() from an empty cell"
        return self.w_value

    def set(self,w_value):
        self.w_value = w_value

    def make_empty(self):
        if self.is_empty():
            raise ValueError, "make_empty() on an empty cell"
        self.w_value = _NoValueInCell

    def is_empty(self):
        return self.w_value is _NoValueInCell

    def __repr__(self):
        """ representation for debugging purposes """
        return "%s(%s)" % (self.__class__.__name__, self.w_value)

    

class W_DictObject(W_Object):
    statictype = W_DictType

    def __init__(w_self, space, list_pairs_w):
        W_Object.__init__(w_self, space)
        w_self.data = [ (w_key, space.unwrap(space.hash(w_key)), Cell(w_value))
                        for w_key,w_value in list_pairs_w ]

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.data)

    def non_empties(self):
        return [ (w_key,cell) for w_key,hash,cell in self.data
                              if not cell.is_empty()]

    def _cell(self,space,w_lookup):
        data = self.data
        # this lookup is where most of the start-up time is consumed.
        # Hashing helps a lot.
        lookup_hash = space.unwrap(space.hash(w_lookup))
        for w_key, hash, cell in data:
            if lookup_hash == hash and space.is_true(space.eq(w_lookup, w_key)):
                break
        else:
            cell = Cell()
            data.append((w_lookup,lookup_hash,cell))
        return cell

    def cell(self,space,w_lookup):
        return space.wrap(self._cell(space,w_lookup))

    def _appendcell(self, space, w_lookup, w_cell):
        # there should be no w_lookup entry already!
        data = self.data
        lookup_hash = space.unwrap(space.hash(w_lookup))
        cell = space.unwrap(w_cell)
        data.append((w_lookup, lookup_hash, cell))

registerimplementation(W_DictObject)


def unwrap__Dict(space, w_dict):
    result = {}
    for w_key, cell in w_dict.non_empties():
        result[space.unwrap(w_key)] = space.unwrap(cell.get())
    return result

def object_init__Dict(space, w_dict, w_args, w_kwds):
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
    data = w_dict.non_empties()
    # XXX shouldn't this use hashing? -- mwh
    for w_key, cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            return cell.get()
    raise OperationError(space.w_KeyError, w_lookup)

def setitem__Dict_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    cell = w_dict._cell(space,w_newkey)
    cell.set(w_newvalue)

def delitem__Dict_ANY(space, w_dict, w_lookup):
    data = w_dict.non_empties()
    for w_key,cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            cell.make_empty()
            return
    raise OperationError(space.w_KeyError, w_lookup)
    
def len__Dict(space, w_dict):
    return space.wrap(len(w_dict.non_empties()))

def contains__Dict_ANY(space, w_dict, w_lookup):
    data = w_dict.non_empties()
    for w_key,cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            return space.w_True
    return space.w_False

def iter__Dict(space, w_dict):
    import iterobject
    w_keys = dict_keys__Dict(space, w_dict)
    return iterobject.W_SeqIterObject(space, w_keys)
    
def eq__Dict_Dict(space, w_left, w_right):
    dataleft = w_left.non_empties()
    dataright = w_right.non_empties()
    if len(dataleft) != len(dataright):
        return space.w_False
    for w_key, cell in dataleft:
        try:
            w_rightval = space.getitem(w_right, w_key)
        except OperationError:
            return space.w_False
        if not space.is_true(space.eq(cell.w_value, w_rightval)):
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
    for w_key, cell in dataleft:
        # This is incorrect, but we need to decide what comparisons on
        # dictionaries of equal size actually means
        # The Python language specification is silent on the subject
        try:
            w_rightval = space.getitem(w_right, w_key)
        except OperationError:
            return space.w_True
        if space.is_true(space.lt(cell.w_value, w_rightval)):
            return space.w_True
    # The dictionaries are equal. This is correct.
    return space.w_False

def dict_copy__Dict(space, w_self):
    return W_DictObject(space, [(w_key,cell.get())
                                      for w_key,cell in
                                      w_self.non_empties()])
def dict_items__Dict(space, w_self):
    return space.newlist([ space.newtuple([w_key,cell.get()])
                           for w_key,cell in
                           w_self.non_empties()])

def dict_keys__Dict(space, w_self):
    return space.newlist([ w_key
                           for w_key,cell in
                           w_self.non_empties()])

def dict_values__Dict(space, w_self):
    return space.newlist([ cell.get()
                           for w_key,cell in
                           w_self.non_empties()])

def dict_has_key__Dict_ANY(space, w_self, w_lookup):
    data = w_self.non_empties()
    # XXX hashing? -- mwh
    for w_key, cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            return space.newbool(1)
    else:
        return space.newbool(0)

def dict_clear__Dict(space, w_self):
    w_self.data = []

def dict_get__Dict_ANY_ANY(space, w_self, w_lookup, w_default):
    data = w_self.non_empties()
    for w_key, cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            return cell.get()
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
register_all(vars(), W_DictType)

