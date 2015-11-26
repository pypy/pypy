from rpython.rlib import rerased
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

    def setitem(self, w_dict, w_key, w_value):
        h = self.unerase(w_dict.dstorage)
        stmdict.setitem(self.space, h, w_key, w_value)
