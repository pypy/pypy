import autopath
from pypy.tool import testit


class TestW_NoneObject(testit.TestCase):

    def setUp(self):
        self.space = testit.objspace('std')

    def tearDown(self):
        pass

    def test_equality(self):
        self.assertEqual_w(self.space.w_None, self.space.w_None)
    
    def test_inequality(self):
        neresult = self.space.ne(self.space.w_None, self.space.w_None)
        self.failIf_w(neresult)

    def test_false(self):
        self.failIf_w(self.space.w_None)
        

if __name__ == '__main__':
    testit.main()
