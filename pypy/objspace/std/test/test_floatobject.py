import autopath
from pypy.tool import test

class FloatTestCase(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace('std')

    def test_float_callable(self):
        self.assertEquals(0.125, float(0.125))

    def test_float_int(self):
        self.assertEquals(42.0, float(42))

    def test_float_string(self):
        self.assertEquals(42.0, float("42"))
        

if __name__ == '__main__':
    test.main()

