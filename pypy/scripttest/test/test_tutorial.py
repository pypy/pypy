import autopath
import os, os.path
from pypy.tool import testit, app_level_diff 

filename = os.path.join(os.path.dirname(__file__), os.pardir, 'tutorial.py')

# Test the functionallity of Guido's tutorial

class TestTutorial(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace()
    def _section_test(self, section):
        diff = app_level_diff.compare(self.space, filename, section)
        if diff:
            raise AssertionError('Tutorial test failed - ' \
                                 "run test_tutorial.details('%s')" % section)
    def test_Section_2_1_2(self):
        self._section_test('Section 2.1.2')
    def test_Section_3_1_1a(self):
        self._section_test('Section 3.1.1a')
##    def xxx_test_Section_3_1_1b(self):
##        self._section_test('Section 3.1.1b')
##    def xxx_test_Section_3_1_1c(self):
##        self._section_test('Section 3.1.1c')
    def test_Section_3_1_2(self):
        self._section_test('Section 3.1.2')
        

def details(section):
    diff = app_level_diff.compare(testit.objspace(), filename, section)
    print diff
    
if __name__ == '__main__':
    testit.main()
