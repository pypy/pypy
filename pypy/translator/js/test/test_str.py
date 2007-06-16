
import py
from pypy.translator.js.test.runtest import JsTest
import pypy.translator.oosupport.test_template.string as oostring


# ====> ../../../rpython/test/test_rstr.py

class TestJsString(JsTest, oostring.BaseTestString):
    def test_char_unichar_eq(self):
        py.test.skip("Cannot test it yet")

    def test_char_unichar_eq_2(self):
        py.test.skip("Cannot test it yet")    
    
    def test_unichar_const(self):
        py.test.skip("Cannot test it yet")

    def test_unichar_eq(self):
        py.test.skip("Cannot test it yet")

    def test_unichar_ord(self):
        py.test.skip("Cannot test it yet")

    def test_unichar_hash(self):
        py.test.skip("Cannot test it yet")

    def test_rfind(self):
        py.test.skip("Not implemented")

    def test_rfind_empty_string(self):
        py.test.skip("Not implemented")

    def test_find_char(self):
        py.test.skip("Not implemented")

    def test_strip(self):
        py.test.skip("Not implemented")
        
    def test_upper(self):
        #XXX Testing machinery is quite confused by js print
        strings = ['', ' ', 'upper', 'UpPeR', ',uppEr,']
        #for i in range(256):
        #    if chr(i) != "\x00" and chr(i) != '(' and chr(i) != '[':
        #        strings.append(chr(i))
        def fn(i):
            return strings[i].upper()
        for i in range(len(strings)):
            res = self.interpret(fn, [i])
            assert self.ll_to_string(res) == fn(i)

    def test_lower(self):
        #XXX Testing machinery is quite confused by js print
        strings = ['', ' ', 'lower', 'LoWeR', ',lowEr,']
        #for i in range(256): strings.append(chr(i))
        def fn(i):
            return strings[i].lower()
        for i in range(len(strings)):
            res = self.interpret(fn, [i])
            assert self.ll_to_string(res) == fn(i)

    def test_strformat(self):
        py.test.skip("string formatting not implemented for base different than 10")

    def test_float(self):
        py.test.skip("returning NaN instead of raising ValueError")

    def test_hash(self):
        py.test.skip("Not implemented")

    def test_hash_value(self):
        py.test.skip("Not implemented")
