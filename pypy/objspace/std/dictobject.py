from pypy.objspace.std.objspace import *
from dicttype import W_DictType
from stringobject import W_StringObject
from pypy.interpreter.extmodule import make_builtin_func

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


registerimplementation(W_DictObject)


def is_true__Dict(space, w_dict):
    return not not w_dict.non_empties()

def unwrap__Dict(space, w_dict):
    result = {}
    for w_key, cell in w_dict.non_empties():
        result[space.unwrap(w_key)] = space.unwrap(cell.get())
    return result

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
    if len(w_left.data) != len(w_right.data):
        return space.newbool(0)
    for w_k, hash, cell in w_left.data:
        try:
            w_v = space.getitem(w_right, w_k)
        except OperationError:
            return space.newbool(0)
        r = space.is_true(space.eq(cell.w_value, w_v))
        if not r:
            return space.newbool(r)
    return space.newbool(1)
        
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
    

register_all(vars(), W_DictType)
