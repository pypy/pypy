import autopath
from pypy.tool import test
from pypy.objspace.std import stringobject
from pypy.objspace.std.stringobject import \
     string_richcompare, W_StringObject, EQ, LT, GT, NE, LE, GE


class TestW_StringObject(test.TestCase):

    def setUp(self):
        self.space = test.objspace('std')

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
                 #original python function
                orf = getattr(str1, '__%s__' % op.lower()) 
                pypyconst = getattr(stringobject, op)
                for str2 in strs:   
                    if orf(str2):
                         self.failUnless_w(
                             string_richcompare(space,
                                                w(str1),
                                                w(str2),
                                                pypyconst))
                    else:
                         self.failIf_w(
                             string_richcompare(space,
                                                w(str1),
                                                w(str2),
                                                pypyconst))
        
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
        if self.space.__class__.__name__.startswith('Trivial'):
            import sys
            if sys.version < (2, 3):
                return
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


#AttributeError: W_StringObject instance has no attribute 'ljust'
#    def test_ljust(self):
#        w = self.space.wrap         
#        s = "abc"
#
#        self.assertEqual_w(w(s).ljust(2), w(s))
#        self.assertEqual_w(w(s).ljust(3), w(s))
#        self.assertEqual_w(w(s).ljust(4), w(s + " "))
#        self.assertEqual_w(w(s).ljust(5), w(s + "  "))    

class TestStringObject(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace('std')

    def test_split(self):
        self.assertEquals("".split(), [])
        self.assertEquals("a".split(), ['a'])
        self.assertEquals(" a ".split(), ['a'])
        self.assertEquals("a b c".split(), ['a','b','c'])
        self.assertEquals('this is the split function'.split(), ['this', 'is', 'the', 'split', 'function'])
        self.assertEquals('a|b|c|d'.split('|'), ['a', 'b', 'c', 'd'])
        self.assertEquals('a|b|c|d'.split('|', 2), ['a', 'b', 'c|d'])
        self.assertEquals('a b c d'.split(None, 1), ['a', 'b c d'])
        self.assertEquals('a b c d'.split(None, 2), ['a', 'b', 'c d'])
        self.assertEquals('a b c d'.split(None, 3), ['a', 'b', 'c', 'd'])
        self.assertEquals('a b c d'.split(None, 4), ['a', 'b', 'c', 'd'])
        self.assertEquals('a b c d'.split(None, 0), ['a b c d'])
        self.assertEquals('a  b  c  d'.split(None, 2), ['a', 'b', 'c  d'])
        self.assertEquals('a b c d '.split(), ['a', 'b', 'c', 'd'])
        self.assertEquals('a//b//c//d'.split('//'), ['a', 'b', 'c', 'd'])
        self.assertEquals('endcase test'.split('test'), ['endcase ', ''])


    def test_split_splitchar(self):
        self.assertEquals("/a/b/c".split('/'), ['','a','b','c'])

    def test_title(self):
        self.assertEquals("brown fox".title(), "Brown Fox")

    def test_capitalize(self):
        self.assertEquals("brown fox".capitalize(), "Brown fox")
        self.assertEquals(' hello '.capitalize(), ' hello ')
        self.assertEquals('Hello '.capitalize(), 'Hello ')
        self.assertEquals('hello '.capitalize(), 'Hello ')
        self.assertEquals('aaaa'.capitalize(), 'Aaaa')
        self.assertEquals('AaAa'.capitalize(), 'Aaaa')

    def test_rjust(self):
        s = "abc"
        self.assertEquals(s.rjust(2), s)
        self.assertEquals(s.rjust(3), s)
        self.assertEquals(s.rjust(4), " " + s)
        self.assertEquals(s.rjust(5), "  " + s)
        self.assertEquals('abc'.rjust(10), '       abc')
        self.assertEquals('abc'.rjust(6), '   abc')
        self.assertEquals('abc'.rjust(3), 'abc')
        self.assertEquals('abc'.rjust(2), 'abc')


    def test_ljust(self):
        s = "abc"
        self.assertEquals(s.ljust(2), s)
        self.assertEquals(s.ljust(3), s)
        self.assertEquals(s.ljust(4), s + " ")
        self.assertEquals(s.ljust(5), s + "  ")
        self.assertEquals('abc'.ljust(10), 'abc       ')
        self.assertEquals('abc'.ljust(6), 'abc   ')
        self.assertEquals('abc'.ljust(3), 'abc')
        self.assertEquals('abc'.ljust(2), 'abc')

    def test_replace(self):
        self.assertEquals('one!two!three!'.replace('!', '@', 1), 'one@two!three!')
        self.assertEquals('one!two!three!'.replace('!', ''), 'onetwothree')
        self.assertEquals('one!two!three!'.replace('!', '@', 2), 'one@two@three!')
        self.assertEquals('one!two!three!'.replace('!', '@', 3), 'one@two@three@')
        self.assertEquals('one!two!three!'.replace('!', '@', 4), 'one@two@three@')
        self.assertEquals('one!two!three!'.replace('!', '@', 0), 'one!two!three!')
        self.assertEquals('one!two!three!'.replace('!', '@'), 'one@two@three@')
        self.assertEquals('one!two!three!'.replace('x', '@'), 'one!two!three!')
        self.assertEquals('one!two!three!'.replace('x', '@', 2), 'one!two!three!')
        self.assertEquals('abc'.replace('', '-'), '-a-b-c-')
        self.assertEquals('abc'.replace('', '-', 3), '-a-b-c')
        self.assertEquals('abc'.replace('', '-', 0), 'abc')
        self.assertEquals(''.replace('', ''), '')
        self.assertEquals('abc'.replace('ab', '--', 0), 'abc')
        self.assertEquals('abc'.replace('xy', '--'), 'abc')
        self.assertEquals('123'.replace('123', ''), '')
        self.assertEquals('123123'.replace('123', ''), '')
        self.assertEquals('123x123'.replace('123', ''), 'x')


    def test_strip(self):
        s = " a b "
        self.assertEquals(s.strip(), "a b")
        self.assertEquals(s.rstrip(), " a b")
        self.assertEquals(s.lstrip(), "a b ")
        self.assertEquals('xyzzyhelloxyzzy'.strip('xyz'), 'hello')
        self.assertEquals('xyzzyhelloxyzzy'.lstrip('xyz'), 'helloxyzzy')
        self.assertEquals('xyzzyhelloxyzzy'.rstrip('xyz'), 'xyzzyhello')

    def test_zfill(self):
        self.assertEquals('123'.zfill(2), '123')
        self.assertEquals('123'.zfill(3), '123')
        self.assertEquals('123'.zfill(4), '0123')
        self.assertEquals('+123'.zfill(3), '+123')
        self.assertEquals('+123'.zfill(4), '+123')
        self.assertEquals('+123'.zfill(5), '+0123')
        self.assertEquals('-123'.zfill(3), '-123')
        self.assertEquals('-123'.zfill(4), '-123')
        self.assertEquals('-123'.zfill(5), '-0123')
        self.assertEquals(''.zfill(3), '000')
        self.assertEquals('34'.zfill(1), '34')
        self.assertEquals('34'.zfill(4), '0034')
            
    def test_center(self):
        s="a b"
        self.assertEquals(s.center(0), "a b")
        self.assertEquals(s.center(1), "a b")
        self.assertEquals(s.center(2), "a b")
        self.assertEquals(s.center(3), "a b")
        self.assertEquals(s.center(4), "a b ")
        self.assertEquals(s.center(5), " a b ")
        self.assertEquals(s.center(6), " a b  ")
        self.assertEquals(s.center(7), "  a b  ")
        self.assertEquals(s.center(8), "  a b   ")
        self.assertEquals(s.center(9), "   a b   ")
        self.assertEquals('abc'.center(10), '   abc    ')
        self.assertEquals('abc'.center(6), ' abc  ')
        self.assertEquals('abc'.center(3), 'abc')
        self.assertEquals('abc'.center(2), 'abc')

        
    def test_count(self):
        self.assertEquals("".count("x"),0)
        self.assertEquals("".count(""),1)
        self.assertEquals("Python".count(""),7)
        self.assertEquals("ab aaba".count("ab"),2)
        self.assertEquals('aaa'.count('a'), 3)
        self.assertEquals('aaa'.count('b'), 0)
        self.assertEquals('aaa'.count('a', -1), 1)
        self.assertEquals('aaa'.count('a', -10), 3)
        self.assertEquals('aaa'.count('a', 0, -1), 2)
        self.assertEquals('aaa'.count('a', 0, -10), 0)
    
    
    def test_startswith(self):
        self.assertEquals('ab'.startswith('ab'),1)
        self.assertEquals('ab'.startswith('a'),1)
        self.assertEquals('ab'.startswith(''),1)
        self.assertEquals('x'.startswith('a'),0)
        self.assertEquals('x'.startswith('x'),1)
        self.assertEquals(''.startswith(''),1)
        self.assertEquals(''.startswith('a'),0)
        self.assertEquals('x'.startswith('xx'),0)
        self.assertEquals('y'.startswith('xx'),0)
                

    def test_endswith(self):
        self.assertEquals('ab'.endswith('ab'),1)
        self.assertEquals('ab'.endswith('b'),1)
        self.assertEquals('ab'.endswith(''),1)
        self.assertEquals('x'.endswith('a'),0)
        self.assertEquals('x'.endswith('x'),1)
        self.assertEquals(''.endswith(''),1)
        self.assertEquals(''.endswith('a'),0)
        self.assertEquals('x'.endswith('xx'),0)
        self.assertEquals('y'.endswith('xx'),0)
      
    def test_expandtabs(self):
        self.assertEquals('abc\rab\tdef\ng\thi'.expandtabs(),    'abc\rab      def\ng       hi')
        self.assertEquals('abc\rab\tdef\ng\thi'.expandtabs(8),   'abc\rab      def\ng       hi')
        self.assertEquals('abc\rab\tdef\ng\thi'.expandtabs(4),   'abc\rab  def\ng   hi')
        self.assertEquals('abc\r\nab\tdef\ng\thi'.expandtabs(4), 'abc\r\nab  def\ng   hi')
        self.assertEquals('abc\rab\tdef\ng\thi'.expandtabs(),    'abc\rab      def\ng       hi')
        self.assertEquals('abc\rab\tdef\ng\thi'.expandtabs(8),   'abc\rab      def\ng       hi')
        self.assertEquals('abc\r\nab\r\ndef\ng\r\nhi'.expandtabs(4), 'abc\r\nab\r\ndef\ng\r\nhi')

        s = 'xy\t'
        self.assertEquals(s.expandtabs(),'xy      ')
        
        s = '\txy\t'
        self.assertEquals(s.expandtabs(),'        xy      ')
        self.assertEquals(s.expandtabs(1),' xy ')
        self.assertEquals(s.expandtabs(2),'  xy  ')
        self.assertEquals(s.expandtabs(3),'   xy ')
        
        self.assertEquals('xy'.expandtabs(),'xy')
        self.assertEquals(''.expandtabs(),'')


    def test_splitlines(self):
        s="ab\nab\n \n  x\n\n\n"
        self.assertEquals(s.splitlines(),['ab',    'ab',  ' ',   '  x',   '',    ''])
        self.assertEquals(s.splitlines(),s.splitlines(0))
        self.assertEquals(s.splitlines(1),['ab\n', 'ab\n', ' \n', '  x\n', '\n', '\n'])
        s="\none\n\two\nthree\n\n"
        self.assertEquals(s.splitlines(),['', 'one', '\two', 'three', ''])
        self.assertEquals(s.splitlines(1),['\n', 'one\n', '\two\n', 'three\n', '\n'])
    
    def test_find(self):
        self.assertEquals('abcdefghiabc'.find('abc'), 0)
        self.assertEquals('abcdefghiabc'.find('abc', 1), 9)
        self.assertEquals('abcdefghiabc'.find('def', 4), -1)

    def test_index(self):
        self.assertEquals('abcdefghiabc'.index(''), 0)
        self.assertEquals('abcdefghiabc'.index('def'), 3)
        self.assertEquals('abcdefghiabc'.index('abc'), 0)
        self.assertEquals('abcdefghiabc'.index('abc', 1), 9)
        #XXX it comes UnicodeError
        #self.assertRaises(ValueError, 'abcdefghiabc'.index('hib'))
        #self.assertRaises(ValueError, 'abcdefghiab'.index('abc', 1))
        #self.assertRaises(ValueError, 'abcdefghi'.index('ghi', 8))
        #self.assertRaises(ValueError, 'abcdefghi'.index('ghi', -1))

    def test_rfind(self):
        self.assertEquals('abcdefghiabc'.rfind('abc'), 9)
        self.assertEquals('abcdefghiabc'.rfind(''), 12)
        self.assertEquals('abcdefghiabc'.rfind('abcd'), 0)
        self.assertEquals('abcdefghiabc'.rfind('abcz'), -1)

    def test_rindex(self):
        self.assertEquals('abcdefghiabc'.rindex(''), 12)
        self.assertEquals('abcdefghiabc'.rindex('def'), 3)
        self.assertEquals('abcdefghiabc'.rindex('abc'), 9)
        self.assertEquals('abcdefghiabc'.rindex('abc', 0, -1), 0)
        #XXX it comes UnicodeError
        #self.assertRaises(ValueError, 'abcdefghiabc'.rindex('hib'))
        #self.assertRaises(ValueError, 'defghiabc'.rindex('def', 1))
        #self.assertRaises(ValueError, 'defghiabc'.rindex('abc', 0, -1))
        #self.assertRaises(ValueError, 'abcdefghi'.rindex('ghi', 0, 8))
        #self.assertRaises(ValueError, 'abcdefghi'.rindex('ghi', 0, -1))


    def test_split_maxsplit(self):
        self.assertEquals("/a/b/c".split('/', 2), ['','a','b/c'])
        self.assertEquals("a/b/c".split("/"), ['a', 'b', 'c'])
        self.assertEquals(" a ".split(None, 0), ['a '])
        self.assertEquals(" a ".split(None, 1), ['a'])
        self.assertEquals(" a a ".split(" ", 0), [' a a '])
        self.assertEquals(" a a ".split(" ", 1), ['', 'a a '])

    def test_join(self):
        self.assertEquals(", ".join(['a', 'b', 'c']), "a, b, c")
        self.assertEquals("".join([]), "")
        self.assertEquals("-".join(['a', 'b']), 'a-b')

    def test_lower(self):
        self.assertEquals("aaa AAA".lower(), "aaa aaa")
        self.assertEquals("".lower(), "")

    def test_upper(self):
        self.assertEquals("aaa AAA".upper(), "AAA AAA")
        self.assertEquals("".upper(), "")
    
    def test_swapcase(self):
        self.assertEquals("aaa AAA 111".swapcase(), "AAA aaa 111")
        self.assertEquals("".swapcase(), "")

    def test_iter(self):
        l=[]
        for i in iter("42"):
            l.append(i)
        self.assertEquals(l, ['4','2'])

if __name__ == '__main__':
    test.main()
