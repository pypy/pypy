# test the integration of unicode and strings (even though we don't
# really implement unicode yet).

import autopath
from pypy.tool import testit


class TestUnicodeStringStdOnly(testit.AppTestCase):
    def setUp(self):
         self.space = testit.objspace('std')

    def test_compares(self):
        self.assertEqual(u'a', 'a')
        self.assertEqual('a', u'a')
        self.assertNotEqual(u'a', 'b')
        self.assertNotEqual('a', u'b')

class TestUnicodeString(testit.AppTestCase):
    def test_addition(self):
        def check(a, b):
            self.assertEqual(a, b)
            self.assertEqual(type(a), type(b))
        check(u'a' + 'b', u'ab')
        check('a' + u'b', u'ab')

    def test_join(self):
        def check(a, b):
            self.assertEqual(a, b)
            self.assertEqual(type(a), type(b))
        check(', '.join([u'a']), u'a')
        check(', '.join(['a', u'b']), u'a, b')
        check(u', '.join(['a', 'b']), u'a, b')

    def test_contains(self):
        self.failUnless(u'' in 'abc')
        self.failUnless(u'a' in 'abc')
        self.failUnless('a' in u'abc')
        

if __name__ == '__main__':
    testit.main()
