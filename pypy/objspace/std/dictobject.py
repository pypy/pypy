from objspace import *
from stringobject import W_StringObject


class W_DictObject:
    delegate_once = {}

    def __init__(self, list_pairs_w):
        self.data = list_pairs_w


def dict_is_true(space, w_dict):
    return not not w_dict.data

StdObjSpace.is_true.register(dict_is_true, W_DictObject)

def getitem_dict_any(space, w_dict, w_lookup):
    data = w_dict.data
    for w_key, w_value in data:
        if space.is_true(space.eq(w_lookup, w_key)):
            return w_value
    raise OperationError(space.w_KeyError, w_lookup)

StdObjSpace.getitem.register(getitem_dict_any, W_DictObject, W_ANY)

def setitem_dict_any_any(space, w_dict, w_newkey, w_newvalue):
    data = w_dict.data
    for i in range(len(data)):
        w_key, w_value = data[i]
        if space.is_true(space.eq(w_newkey, w_key)):
            # replace existing value
            data[i] = w_key, w_newvalue
            #print 'dict replace %s:' % w_newkey, data
            return
    # add new (key,value) pair
    data.append((w_newkey, w_newvalue))
    #print 'dict append %s:' % w_newkey, data

StdObjSpace.setitem.register(setitem_dict_any_any, W_DictObject, W_ANY, W_ANY)
