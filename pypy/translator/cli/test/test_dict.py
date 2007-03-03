import py
from pypy.translator.cli.test.runtest import CliTest
import pypy.translator.oosupport.test_template.dict as oodict

class TestCliDict(CliTest, oodict.BaseTestDict):
    def test_dict_of_dict(self):
        py.test.skip("CLI doesn't support recursive dicts")

    def test_recursive(self):
        py.test.skip("CLI doesn't support recursive dicts")


class TestCliEmptyDict(CliTest, oodict.BaseTestEmptyDict):
    pass

class TestCliConstantDict(CliTest, oodict.BaseTestConstantDict):
    pass
