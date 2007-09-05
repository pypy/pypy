import py
from pypy.translator.oosupport.test_template.runtest import BaseTestRunTest
from pypy.translator.cli.test.runtest import CliTest

class TestRunTest(BaseTestRunTest, CliTest):

    def test_auto_raise_exc(self):
        def fn():
            raise ValueError
        f = self._compile(fn, [], auto_raise_exc=True)
        py.test.raises(ValueError, f)
