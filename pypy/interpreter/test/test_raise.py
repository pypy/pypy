import autopath
from pypy.tool import testit


class AppTestRaise(testit.AppTestCase):
    def test_control_flow(self):
        try:
            raise Exception
            self.fail("exception failed to raise")
        except:
            pass
        else:
            self.fail("exception executing else clause!")

    def test_1arg(self):
        try:
            raise SystemError, 1
        except Exception, e:
            self.assertEquals(e.args[0], 1)

    def test_2args(self):
        try:
            raise SystemError, (1, 2)
        except Exception, e:
            self.assertEquals(e.args[0], 1)
            self.assertEquals(e.args[1], 2)

    def test_instancearg(self):
        try:
            raise SystemError, SystemError(1, 2)
        except Exception, e:
            self.assertEquals(e.args[0], 1)
            self.assertEquals(e.args[1], 2)

    def test_more_precise_instancearg(self):
        try:
            raise Exception, SystemError(1, 2)
        except SystemError, e:
            self.assertEquals(e.args[0], 1)
            self.assertEquals(e.args[1], 2)

    def test_stringexc(self):
        a = "hello world"
        try:
            raise a
        except a, e:
            self.assertEquals(e, None)
        try:
            raise a, "message"
        except a, e:
            self.assertEquals(e, "message")

    def test_builtin_exc(self):
        try:
            [][0]
        except IndexError, e:
            self.assert_(isinstance(e, IndexError))

    def test_raise_cls(self):
        def f():
            raise IndexError
        self.assertRaises(IndexError, f)

    def test_raise_cls_catch(self):
        def f(r):
            try:
                raise r
            except LookupError:
                return 1
        self.assertRaises(Exception, f, Exception)
        self.assertEquals(f(IndexError), 1)

    def test_raise_wrong(self):
        try:
            raise 1
        except TypeError:
            pass
        else:
            self.fail("shouldn't be able to raise 1")

    def test_raise_three_args(self):
        import sys
        try:
            raise ValueError
        except:
            exc_type,exc_val,exc_tb = sys.exc_info()
        try:
            raise exc_type,exc_val,exc_tb
        except:
            exc_type2,exc_val2,exc_tb2 = sys.exc_info()
        self.assertEquals(exc_type,exc_type2)
        self.assertEquals(exc_val,exc_val2)
        self.assertEquals(exc_tb,exc_tb2)

    def test_tuple_type(self):
        def f():
            raise ((StopIteration, 123), 456, 789)
        self.assertRaises(StopIteration, f)

    def test_userclass(self):
        class A:
            def __init__(self, x=None):
                self.x = x
        class B(A):
            pass
        try:
            raise A
        except A, a:
            self.assertEquals(a.x, None)
        try:
            raise A(42)
        except A, a:
            self.assertEquals(a.x, 42)
        try:
            raise A, 42
        except A, a:
            self.assertEquals(a.x, 42)
        try:
            raise B
        except A, b:
            self.assertEquals(type(b), B)
        try:
            raise A, B(42)
        except B, b:
            self.assertEquals(type(b), B)
            self.assertEquals(b.x, 42)

if __name__ == '__main__':
    testit.main()
