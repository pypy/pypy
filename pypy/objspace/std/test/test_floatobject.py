import autopath
from pypy.objspace.std import floatobject as fobj
from pypy.objspace.std.objspace import FailedToImplement
from pypy.tool import test

class TestW_FloatObject(test.TestCase):

    def setUp(self):
        self.space = test.objspace('std')

    def tearDown(self):
        pass
    
    def _unwrap_nonimpl(self, func, *args, **kwds):
        """ make sure that the expected exception occurs, and unwrap it """
        try:
            res = func(*args, **kwds)
            raise Exception, "should have failed but returned '%s'!" %repr(res)
        except FailedToImplement, arg:
            return arg[0]

    def test_pow_fff(self):
        x = 10.0
        y = 2.0
        z = 13.0
        f1 = fobj.W_FloatObject(self.space, x)
        f2 = fobj.W_FloatObject(self.space, y)
        f3 = fobj.W_FloatObject(self.space, z)
        self.assertEquals(self.space.w_TypeError,
                          self._unwrap_nonimpl(fobj.pow__Float_Float_ANY, self.space, f1, f2, f3))

    def test_pow_ffn(self):
        x = 10.0
        y = 2.0
        f1 = fobj.W_FloatObject(self.space, x)
        f2 = fobj.W_FloatObject(self.space, y)
        v = fobj.pow__Float_Float_ANY(self.space, f1, f2, self.space.w_None)
        self.assertEquals(v.floatval, x ** y)

class AppFloatTest(test.AppTestCase):
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

