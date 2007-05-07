
import py
from pypy.rpython.test.test_rdict import BaseTestRdict
from pypy.translator.js.test.runtest import JsTest

# ====> ../../../rpython/test/test_rdict.py

class TestJsDict(JsTest, BaseTestRdict):
    def test_tuple_dict(self):
        py.test.skip("rdict not implemented")

    def test_dict_itermethods(self):
        py.test.skip("itermethods not implemented")

    def test_dict_copy(self):
        py.test.skip("itermethods not implemented")

    def test_dict_update(self):
        py.test.skip("itermethods not implemented")

    def test_dict_inst_iterkeys(self):
        py.test.skip("itermethods not implemented")

    def test_dict_values(self):
        py.test.skip("itermethods not implemented")

    def test_dict_inst_values(self):
        py.test.skip("itermethods not implemented")

    def test_dict_inst_itervalues(self):
        py.test.skip("itermethods not implemented")

    def test_dict_items(self):
        py.test.skip("itermethods not implemented")

    def test_dict_inst_items(self):
        py.test.skip("itermethods not implemented")

    def test_dict_inst_iteritems(self):
        py.test.skip("itermethods not implemented")


    def test_specific_obscure_bug(self):
        py.test.skip("rdict not implemented")

