
import py
#from pypy.tool.pytest.confpath import testresultdir
from pypy.tool.pytest.result import ResultFromMime
testpath = py.magic.autopath().dirpath('data')

class TestResultCache:

    def test_timeout(self):
        test = ResultFromMime(testpath.join('test___all__.txt'))
        assert test.ratio_of_passed() == 0.

    def test_passed(self):
        test = ResultFromMime(testpath.join('test_sys.txt'))
        assert test.ratio_of_passed() == 1.

    def test_unittest_partial(self):
        test = ResultFromMime(testpath.join('test_compile.txt'))
        assert test.ratio_of_passed() == 10./15
    
    def test_doctest_of(self):
        test = ResultFromMime(testpath.join('test_generators.txt'))
        assert test.ratio_of_passed() == 133./154

    def test_doctest_slash(self):
        test = ResultFromMime(testpath.join('test_descr.txt'))
        assert test.ratio_of_passed() == 65./92

    def test_fail(self):
        test = ResultFromMime(testpath.join('test_global.txt'))
        assert test.ratio_of_passed() == 0.

