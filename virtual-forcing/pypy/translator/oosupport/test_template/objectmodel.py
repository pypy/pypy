import py
from pypy.rlib.test.test_objectmodel import BaseTestObjectModel as RLibBase


class BaseTestObjectModel(RLibBase):
    def test_rdict_of_void_copy(self):
        from pypy.rlib.test.test_objectmodel import r_dict, strange_key_eq, strange_key_hash
        def fn():
            d = r_dict(strange_key_eq, strange_key_hash)
            d['hello'] = None
            d['world'] = None
            d1 = d.copy()
            return len(d1)
        assert self.interpret(fn, []) == 2

