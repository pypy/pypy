import testsupport
import pypy.objspace.std.stringobject as so

from pypy.objspace.std.stringobject import string_richcompare, W_StringObject, EQ, LT, GT, NE, LE, GE
from pypy.objspace.std.objspace import StdObjSpace


class TestW_StringObject(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.objspace()

    def tearDown(self):
        pass

    def test_order_rich(self):
        space = self.space
        def w(txt):
             return W_StringObject(space, txt)
        strs = ['ala', 'bla', 'ala', 'alaaa', '', 'b']
        ops = [ 'EQ', 'LT', 'GT', 'NE', 'LE', 'GE' ]

        while strs[1:]:
            str1 = strs.pop()
            for op in ops:
                orf = getattr(str1, '__%s__' % op.lower())  #original python function
                pypyconst = getattr(so, op)
                for str2 in strs:   
                    if orf(str2):
                         self.failUnless_w(string_richcompare(space, w(str1), w(str2), pypyconst))
                    else:
                         self.failIf_w(string_richcompare(space, w(str1), w(str2), pypyconst))
        
        

    def test_equality(self):
        w = self.space.wrap 
        self.assertEqual_w(w('abc'), w('abc'))
        self.assertNotEqual_w(w('abc'), w('def'))

    def test_order_cmp(self):
        space = self.space
        w = space.wrap
        self.failUnless_w(space.lt(w('a'), w('b')))
        self.failUnless_w(space.lt(w('a'), w('ab')))
        self.failUnless_w(space.le(w('a'), w('a')))
        self.failUnless_w(space.gt(w('a'), w('')))

    def test_truth(self):
        w = self.space.wrap
        self.failUnless_w(w('non-empty'))
        self.failIf_w(w(''))

    def test_getitem(self):
        space = self.space
        w = space.wrap
        w_str = w('abc')
        self.assertEqual_w(space.getitem(w_str, w(0)), w('a'))
        self.assertEqual_w(space.getitem(w_str, w(-1)), w('c'))
        self.assertRaises_w(space.w_IndexError,
                            space.getitem,
                            w_str,
                            w(3))

    def test_slice(self):
        space = self.space
        w = space.wrap
        w_str = w('abc')

        w_slice = space.newslice(w(0), w(0), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w(''))

        w_slice = space.newslice(w(0), w(1), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('a'))

        w_slice = space.newslice(w(0), w(10), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('abc'))

        w_slice = space.newslice(space.w_None, space.w_None, None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('abc'))

        w_slice = space.newslice(space.w_None, w(-1), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('ab'))

        w_slice = space.newslice(w(-1), space.w_None, None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('c'))

    def test_extended_slice(self):
        space = self.space
        w_None = space.w_None
        w = space.wrap
        w_str = w('hello')

        w_slice = space.newslice(w_None, w_None, w(1))
        self.assertEqual_w(space.getitem(w_str, w_slice), w('hello'))

        w_slice = space.newslice(w_None, w_None, w(-1))
        self.assertEqual_w(space.getitem(w_str, w_slice), w('olleh'))

        w_slice = space.newslice(w_None, w_None, w(2))
        self.assertEqual_w(space.getitem(w_str, w_slice), w('hlo'))

        w_slice = space.newslice(w(1), w_None, w(2))
        self.assertEqual_w(space.getitem(w_str, w_slice), w('el'))



if __name__ == '__main__':
    testsupport.main()
