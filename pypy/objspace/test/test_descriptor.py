import autopath
from pypy.tool import testit
    
class Test_Descriptor(testit.AppTestCase):

    def test_non_data_descr(self):
        class X(object):
            def f(self):
                return 42
        x = X()
        self.assertEquals(x.f(), 42)
        x.f = 43
        self.assertEquals(x.f, 43)
        del x.f
        self.assertEquals(x.f(), 42)

    def test_member(self):
        import sys
        self.assertEquals(sys.stdin.softspace, 0)
        self.assertEquals(file.softspace.__get__(sys.stdin), 0)
        sys.stdin.softspace = 1
        self.assertEquals(sys.stdin.softspace, 1)
        file.softspace.__set__(sys.stdin, 0)
        self.assertEquals(sys.stdin.softspace, 0)
        self.assertRaises(TypeError, delattr, sys.stdin, 'softspace')
        self.assertRaises(TypeError, file.softspace.__delete__, sys.stdin)

if __name__ == '__main__':
    testit.main()
