from objspace import *
from stringobject import W_StringObject


class _NoValueInCell: pass

class Cell:
    def __init__(self,w_value=_NoValueInCell):
        self.w_value = w_value

    def get(self):
        if self.is_empty():
            raise OperatioError(w_SystemError)
        return self.w_value

    def set(self,w_value):
        self.w_value = w_value

    def make_empty(self):
        if self.is_empty():
            raise OperatioError(w_SystemError)
        self.w_value = _NoValueInCell

    def is_empty(self):
        return self.w_value is _NoValueInCell
    

class W_DictObject(W_Object):
    delegate_once = {}

    def __init__(w_self, space, list_pairs_w):
        W_Object.__init__(w_self, space)
        w_self.data = [ (w_key,Cell(w_value)) for w_key,w_value in list_pairs_w ]

    def non_empties(self):
        return [ (w_key,cell) for w_key,cell in self.data if not cell.is_empty()]

    def _cell(self,space,w_lookup):
        data = self.data
        for w_key, cell in data:
            if space.is_true(space.eq(w_lookup, w_key)):
                break
        else:
            cell = Cell()
            data.append((w_lookup,cell))
        return cell

    def cell(self,space,w_lookup):
        return space.wrap(self._cell(space,w_lookup))
                
def dict_is_true(space, w_dict):
    return not not w_dict.non_empties()

StdObjSpace.is_true.register(dict_is_true, W_DictObject)

def dict_unwrap(space, w_dict):
    result = {}
    for w_key, cell in w_dict.non_empties():
        result[space.unwrap(w_key)] = space.unwrap(cell.get())
    return result

StdObjSpace.unwrap.register(dict_unwrap, W_DictObject)

def getitem_dict_any(space, w_dict, w_lookup):
    data = w_dict.non_empties()
    for w_key, cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            return cell.get()
    raise OperationError(space.w_KeyError, w_lookup)

StdObjSpace.getitem.register(getitem_dict_any, W_DictObject, W_ANY)

def setitem_dict_any_any(space, w_dict, w_newkey, w_newvalue):
    cell = w_dict._cell(space,w_newkey)
    cell.set(w_newvalue)

StdObjSpace.setitem.register(setitem_dict_any_any, W_DictObject, W_ANY, W_ANY)

def delitem_dict_any(space, w_dict, w_lookup):
    data = w_dict.non_empties()
    for w_key,cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            cell.make_empty()
            return
    raise OperationError(space.w_KeyError, w_lookup)
    
StdObjSpace.delitem.register(delitem_dict_any, W_DictObject, W_ANY)

def len_dict(space, w_dict):
    return space.wrap(len(w_dict.non_empties()))

StdObjSpace.len.register(len_dict, W_DictObject)

def contains_dict_any(space, w_dict, w_lookup):
    data = w_dict.non_empties()
    for w_key,cell in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            return space.w_True
    return space.w_False

StdObjSpace.contains.register(contains_dict_any, W_DictObject, W_ANY)
