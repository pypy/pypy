import autopath
from pypy.tool import testit


class TestW_BoolObject(testit.TestCase):

    def setUp(self):
        self.space = testit.objspace('std')
        self.true = self.space.w_True
        self.false = self.space.w_False
        self.wrap = self.space.wrap

    def tearDown(self):
        pass

    def test_repr(self):
        self.assertEqual_w(self.space.repr(self.true), self.wrap("True"))
        self.assertEqual_w(self.space.repr(self.false), self.wrap("False"))
    
    def test_true(self):
        self.failUnless_w(self.true)
        
    def test_false(self):
        self.failIf_w(self.false)
        
class AppBoolTest(testit.AppTestCase):
    def setUp(self):
        self.space = testit.objspace('std')

    def test_bool_callable(self):
        self.assertEquals(True, bool(1))
        self.assertEquals(False, bool(0))
        self.assertEquals(False, bool())

    def test_bool_string(self):
        self.assertEquals("True", str(True))
        self.assertEquals("False", str(False))
        self.assertEquals("True", repr(True))
        self.assertEquals("False", repr(False))

if __name__ == '__main__':
    testit.main()
