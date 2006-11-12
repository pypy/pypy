# some tests stolen from the standard test suite
# XXX find a way to more systematically test these test suites
import py
from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
from pypy.lang.prolog.interpreter.test.tool import collect_all, assert_true, assert_false

class TestSec78(object):
    def test_common(self):
        assert_false('fail.')
        assert_true('true.')

    def DONOTtest_cut(self):
        assert_true('!.')
