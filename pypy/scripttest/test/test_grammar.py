import autopath
import os, os.path
from pypy.tool import testit, app_level_diff 

filename = os.path.join(os.path.dirname(__file__), os.pardir, 'grammar.py')

# Test the functionallity of the CPython test_grammar.py regression test

class TestGrammar(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace()
    def _section_test(self, section):
        diff = app_level_diff.compare(self.space, filename, section)
        if diff:
            raise AssertionError('Tutorial test failed - ' \
                                 "run test_grammar.details('%s')" % section)
    def test_Section_1(self):
        self._section_test('Section 1.')
##    def xxx_test_Section_lambdef(self):
##        self._section_test('Section lambdef')
    def test_Section_simple_stmt(self):
        self._section_test('Section simple_stmt')
    def test_Section_extended_print_stmt(self):
        self._section_test('Section extended print_stmt')
    def test_Section_pass_stmt(self):
        self._section_test('Section pass_stmt')
    def test_Section_continue_stmt(self):
        self._section_test('Section continue_stmt')
    def test_Section_return_stmt(self):
        self._section_test('Section return_stmt')
    def test_Section_global_stmt(self):
        self._section_test('Section global_stmt')
##    def xxx_test_Section_exec_stmt(self):
##        self._section_test('Section exec_stmt')
    def test_Section_assert_stmt(self):
        self._section_test('Section assert_stmt')
##    def xxx_test_Section_list_comps(self):
##        self._section_test('Section list_comps')
        

def details(section):
    diff = app_level_diff.compare(testit.objspace(), filename, section)
    print diff
    
if __name__ == '__main__':
    testit.main()
