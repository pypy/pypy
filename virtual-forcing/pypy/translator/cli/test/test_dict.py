import py
from pypy.translator.cli.test.runtest import CliTest
import pypy.translator.oosupport.test_template.dict as oodict

class TestCliDict(CliTest, oodict.BaseTestDict):
    def test_dict_of_dict(self):
        py.test.skip("CLI doesn't support recursive dicts")

    def test_recursive(self):
        py.test.skip("CLI doesn't support recursive dicts")

    def test_dict_of_void_special_case(self):
        def fn(n):
            d = {}
            for i in xrange(n):
                d[i] = None
            return d[0]
        assert self.interpret(fn, [2]) is None

    def test_dict_with_void_key(self):
        def fn(flag):
            d = {}
            if flag:
                d[None] = flag
            return bool(d)
        res = self.interpret(fn, [42])
        assert res is True

##   XXX: it fails because of a bug in the annotator, which thinks the
##   last line always raises
##    def test_dict_with_void_key_pbc(self):
##        d = {}
##        def fn(flag):
##            if flag:
##                d[None] = flag
##            return d[None]
##        res = self.interpret(fn, [42], backendopt=False)
##        assert res == 42

class TestCliEmptyDict(CliTest, oodict.BaseTestEmptyDict):
    pass

class TestCliConstantDict(CliTest, oodict.BaseTestConstantDict):
    pass
