import autopath
from pypy.tool import testit


class TestClassApp(testit.AppTestCase):

    
    def test_class(self):
        class C:
            pass
        self.assertEquals(C.__class__, type)
        c = C()
        self.assertEquals(c.__class__, C)

    def dont_test_metaclass_explicit(self):
        class M(type):
            pass
        class C:
            __metaclass__ = M
        self.assertEquals(C.__class__, M)
        c = C()
        self.assertEquals(c.__class__, C)

    def dont_test_metaclass_inherited(self):
        class M(type):
            pass
        class B:
            __metaclass__ = M
        class C(B):
            pass
        self.assertEquals(C.__class__, M)
        c = C()
        self.assertEquals(c.__class__, C)

    def dont_test_metaclass_global(self):
        d = {}
        metatest_text = """
class M(type):
    pass
__metaclass__ = M
class C:
    pass
"""
        exec metatest_text in d
        C = d['C']
        M = d['M']
        self.assertEquals(C.__class__, M)
        c = C()
        self.assertEquals(c.__class__, C)

    def test_method(self):
        class C:
            def meth(self):
                return 1
        c = C()
        self.assertEqual(c.meth(), 1)

    def test_method_exc(self):
        class C:
            def meth(self):
                raise RuntimeError
        c = C()
        self.assertRaises(RuntimeError, c.meth)
            
        
if __name__ == '__main__':
    testit.main()
