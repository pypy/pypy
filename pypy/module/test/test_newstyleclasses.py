import autopath

from pypy.tool import test

class TestBuiltinApp(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace()

    def test_staticmethod(self):
        class C:
            def f(a, b):
                return a+b
            f = staticmethod(f)
        class D(C):
            pass

        c = C()
        d = D()
        self.assertEquals(c.f("abc", "def"), "abcdef")
        self.assertEquals(C.f("abc", "def"), "abcdef")
        self.assertEquals(d.f("abc", "def"), "abcdef")
        self.assertEquals(D.f("abc", "def"), "abcdef")

    def test_classmethod(self):
        class C:
            def f(cls, stuff):
                return cls, stuff
            f = classmethod(f)
        class D(C):
            pass

        c = C()
        d = D()
        self.assertEquals(c.f("abc"), (C, "abc"))
        self.assertEquals(C.f("abc"), (C, "abc"))
        self.assertEquals(d.f("abc"), (D, "abc"))
        self.assertEquals(D.f("abc"), (D, "abc"))


if __name__ == '__main__':
    test.main()
