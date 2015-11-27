from rpython.rlib import rerased, objectmodel
from pypy.objspace.std.dictmultiobject import (DictStrategy,
                                               create_iterator_classes)
from pypy.module.pypystm import stmdict


class StmDictStrategy(DictStrategy):
    erase, unerase = rerased.new_erasing_pair("stm")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def get_empty_storage(self):
        return self.erase(stmdict.create())

    def length(self, w_dict):
        h = self.unerase(w_dict.dstorage)
        return stmdict.get_length(self.space, h)

    def getitem(self, w_dict, w_key):
        h = self.unerase(w_dict.dstorage)
        return stmdict.getitem(self.space, h, w_key)

    def getitem_str(self, w_dict, key):
        return self.getitem(w_dict, self.space.wrap(key))

    def setitem(self, w_dict, w_key, w_value):
        h = self.unerase(w_dict.dstorage)
        stmdict.setitem(self.space, h, w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        self.setitem(w_dict, self.space.wrap(key), w_value)

    def delitem(self, w_dict, w_key):
        h = self.unerase(w_dict.dstorage)
        stmdict.delitem(self.space, h, w_key)

    def setdefault(self, w_dict, w_key, w_default):
        h = self.unerase(w_dict.dstorage)
        return stmdict.setdefault(self.space, h, w_key, w_default)

    def popitem(self, w_dict):
        space = self.space
        h = self.unerase(w_dict.dstorage)
        return space.newtuple(stmdict.popitem(space, h))

    def getiterkeys(self, w_dict):
        h = self.unerase(w_dict.dstorage)
        return StmDictIterKeys(self.space, h)

    def getitervalues(self, w_dict):
        h = self.unerase(w_dict.dstorage)
        return StmDictIterValues(self.space, h)

    def getiteritems_with_hash(self, w_dict):
        h = self.unerase(w_dict.dstorage)
        return StmDictIterItemsWithHash(self.space, h)

    def clear(self, w_dict):
        w_dict.dstorage = self.get_empty_storage()

    def w_keys(self, w_dict):
        space = self.space
        h = self.unerase(w_dict.dstorage)
        return space.newlist(stmdict.get_keys_values_w(space, h, offset=0))

    def values(self, w_dict):
        h = self.unerase(w_dict.dstorage)
        return stmdict.get_keys_values_w(self.space, h, offset=1)

    def items(self, w_dict):
        space = self.space
        h = self.unerase(w_dict.dstorage)
        return space.newlist(stmdict.get_items_w(space, h))

    # XXX these two methods should also be implemented for extra performance
    #def prepare_update(self, w_dict, num_extra):
    #def setitem_untyped(self, dstorage, key, w_value, keyhash):


class BaseStmDictIter(object):
    objectmodel.import_from_mixin(stmdict.BaseSTMDictIter)

    def __iter__(self):
        return self

    def _cleanup_(self):
        raise Exception("seeing a prebuilt %r object" % (
            self.__class__,))

class StmDictIterKeys(BaseStmDictIter):
    def get_final_value(self, hash, array, index):
        return stmdict.unerase(array[index])

class StmDictIterValues(BaseStmDictIter):
    def get_final_value(self, hash, array, index):
        return stmdict.unerase(array[index + 1])

class StmDictIterItemsWithHash(BaseStmDictIter):
    def get_final_value(self, hash, array, index):
        w_key = stmdict.unerase(array[index])
        w_value = stmdict.unerase(array[index + 1])
        return (w_key, w_value, hash)


create_iterator_classes(StmDictStrategy)
