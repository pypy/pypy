import autopath
from pypy.tool import testit

# NB. instmethobject.py has been removed,
# but the following tests still make sense

class TestInstMethObjectApp(testit.AppTestCase):
    def setUp(self):
        self.space = testit.objspace('std')

    def test_callBound(self):
        boundMethod = [1,2,3].__len__
        self.assertEquals(boundMethod(), 3)
        self.assertRaises(TypeError, boundMethod, 333)
    def test_callUnbound(self):
        unboundMethod = list.__len__
        self.assertEquals(unboundMethod([1,2,3]), 3)
        self.assertRaises(TypeError, unboundMethod)
        self.assertRaises(TypeError, unboundMethod, 333)
        self.assertRaises(TypeError, unboundMethod, [1,2,3], 333)

if __name__ == '__main__':
    testit.main()
