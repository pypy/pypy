from pypy.objspace.std import stringobject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.conftest import gettestobjspace


class TestW_StringObject:

    def teardown_method(self, method):
        pass

    def test_str_w(self):
        assert self.space.str_w(self.space.wrap("foo")) == "foo"

    def test_equality(self):
        w = self.space.wrap 
        assert self.space.eq_w(w('abc'), w('abc'))
        assert not self.space.eq_w(w('abc'), w('def'))

    def test_order_cmp(self):
        space = self.space
        w = space.wrap
        assert self.space.is_true(space.lt(w('a'), w('b')))
        assert self.space.is_true(space.lt(w('a'), w('ab')))
        assert self.space.is_true(space.le(w('a'), w('a')))
        assert self.space.is_true(space.gt(w('a'), w('')))

    def test_truth(self):
        w = self.space.wrap
        assert self.space.is_true(w('non-empty'))
        assert not self.space.is_true(w(''))

    def test_getitem(self):
        space = self.space
        w = space.wrap
        w_str = w('abc')
        assert self.space.eq_w(space.getitem(w_str, w(0)), w('a'))
        assert self.space.eq_w(space.getitem(w_str, w(-1)), w('c'))
        self.space.raises_w(space.w_IndexError,
                            space.getitem,
                            w_str,
                            w(3))

    def test_slice(self):
        space = self.space
        w = space.wrap
        w_str = w('abc')

        w_slice = space.newslice(w(0), w(0), space.w_None)
        assert self.space.eq_w(space.getitem(w_str, w_slice), w(''))

        w_slice = space.newslice(w(0), w(1), space.w_None)
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('a'))

        w_slice = space.newslice(w(0), w(10), space.w_None)
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('abc'))

        w_slice = space.newslice(space.w_None, space.w_None, space.w_None)
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('abc'))

        w_slice = space.newslice(space.w_None, w(-1), space.w_None)
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('ab'))

        w_slice = space.newslice(w(-1), space.w_None, space.w_None)
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('c'))

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
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('hello'))

        w_slice = space.newslice(w_None, w_None, w(-1))
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('olleh'))

        w_slice = space.newslice(w_None, w_None, w(2))
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('hlo'))

        w_slice = space.newslice(w(1), w_None, w(2))
        assert self.space.eq_w(space.getitem(w_str, w_slice), w('el'))

class AppTestStringObject:

    def test_format_wrongchar(self):
        raises(ValueError, 'a%Zb'.__mod__, ((23,),))

    def test_format(self):
        raises(TypeError, "foo".__mod__, "bar")
        raises(TypeError, u"foo".__mod__, "bar")
        raises(TypeError, "foo".__mod__, u"bar")

        for format, arg, cls in [("a %s b", "foo", str),
                                 (u"a %s b", "foo", unicode),
                                 ("a %s b", u"foo", unicode),
                                 (u"a %s b", u"foo", unicode)]:
            raises(TypeError, format[:2].__mod__, arg)
            result = format % arg
            assert result == "a foo b"
            assert isinstance(result, cls)

    def test_split(self):
        assert "".split() == []
        assert "".split('x') == ['']
        assert " ".split() == []
        assert "a".split() == ['a']
        assert "a".split("a", 1) == ['', '']
        assert " ".split(" ", 1) == ['', '']
        assert "aa".split("a", 2) == ['', '', '']
        assert " a ".split() == ['a']
        assert "a b c".split() == ['a','b','c']
        assert 'this is the split function'.split() == ['this', 'is', 'the', 'split', 'function']
        assert 'a|b|c|d'.split('|') == ['a', 'b', 'c', 'd']
        assert 'a|b|c|d'.split('|', 2) == ['a', 'b', 'c|d']
        assert 'a b c d'.split(None, 1) == ['a', 'b c d']
        assert 'a b c d'.split(None, 2) == ['a', 'b', 'c d']
        assert 'a b c d'.split(None, 3) == ['a', 'b', 'c', 'd']
        assert 'a b c d'.split(None, 4) == ['a', 'b', 'c', 'd']
        assert 'a b c d'.split(None, 0) == ['a b c d']
        assert 'a  b  c  d'.split(None, 2) == ['a', 'b', 'c  d']
        assert 'a b c d '.split() == ['a', 'b', 'c', 'd']
        assert 'a//b//c//d'.split('//') == ['a', 'b', 'c', 'd']
        assert 'endcase test'.split('test') == ['endcase ', '']
        raises(ValueError, 'abc'.split, '')

    def test_rsplit(self):
        assert "".rsplit() == []
        assert " ".rsplit() == []
        assert "a".rsplit() == ['a']
        assert "a".rsplit("a", 1) == ['', '']
        assert " ".rsplit(" ", 1) == ['', '']
        assert "aa".rsplit("a", 2) == ['', '', '']
        assert " a ".rsplit() == ['a']
        assert "a b c".rsplit() == ['a','b','c']
        assert 'this is the rsplit function'.rsplit() == ['this', 'is', 'the', 'rsplit', 'function']
        assert 'a|b|c|d'.rsplit('|') == ['a', 'b', 'c', 'd']
        assert 'a|b|c|d'.rsplit('|', 2) == ['a|b', 'c', 'd']
        assert 'a b c d'.rsplit(None, 1) == ['a b c', 'd']
        assert 'a b c d'.rsplit(None, 2) == ['a b', 'c', 'd']
        assert 'a b c d'.rsplit(None, 3) == ['a', 'b', 'c', 'd']
        assert 'a b c d'.rsplit(None, 4) == ['a', 'b', 'c', 'd']
        assert 'a b c d'.rsplit(None, 0) == ['a b c d']
        assert 'a  b  c  d'.rsplit(None, 2) == ['a  b', 'c', 'd']
        assert 'a b c d '.rsplit() == ['a', 'b', 'c', 'd']
        assert 'a//b//c//d'.rsplit('//') == ['a', 'b', 'c', 'd']
        assert 'endcase test'.rsplit('test') == ['endcase ', '']
        raises(ValueError, 'abc'.rsplit, '')

    def test_split_splitchar(self):
        assert "/a/b/c".split('/') == ['','a','b','c']

    def test_title(self):
        assert "brown fox".title() == "Brown Fox"
        assert "!brown fox".title() == "!Brown Fox"
        assert "bROWN fOX".title() == "Brown Fox"
        assert "Brown Fox".title() == "Brown Fox"
        assert "bro!wn fox".title() == "Bro!Wn Fox"

    def test_istitle(self):
        assert "".istitle() == False
        assert "!".istitle() == False
        assert "!!".istitle() == False
        assert "brown fox".istitle() == False
        assert "!brown fox".istitle() == False
        assert "bROWN fOX".istitle() == False
        assert "Brown Fox".istitle() == True
        assert "bro!wn fox".istitle() == False
        assert "Bro!wn fox".istitle() == False
        assert "!brown Fox".istitle() == False
        assert "!Brown Fox".istitle() == True
        assert "Brow&&&&N Fox".istitle() == True
        assert "!Brow&&&&n Fox".istitle() == False
        
    def test_capitalize(self):
        assert "brown fox".capitalize() == "Brown fox"
        assert ' hello '.capitalize() == ' hello '
        assert 'Hello '.capitalize() == 'Hello '
        assert 'hello '.capitalize() == 'Hello '
        assert 'aaaa'.capitalize() == 'Aaaa'
        assert 'AaAa'.capitalize() == 'Aaaa'

    def test_rjust(self):
        s = "abc"
        assert s.rjust(2) == s
        assert s.rjust(3) == s
        assert s.rjust(4) == " " + s
        assert s.rjust(5) == "  " + s
        assert 'abc'.rjust(10) == '       abc'
        assert 'abc'.rjust(6) == '   abc'
        assert 'abc'.rjust(3) == 'abc'
        assert 'abc'.rjust(2) == 'abc'
        assert 'abc'.rjust(5, '*') == '**abc'     # Python 2.4
        raises(TypeError, 'abc'.rjust, 5, 'xx')

    def test_ljust(self):
        s = "abc"
        assert s.ljust(2) == s
        assert s.ljust(3) == s
        assert s.ljust(4) == s + " "
        assert s.ljust(5) == s + "  "
        assert 'abc'.ljust(10) == 'abc       '
        assert 'abc'.ljust(6) == 'abc   '
        assert 'abc'.ljust(3) == 'abc'
        assert 'abc'.ljust(2) == 'abc'
        assert 'abc'.ljust(5, '*') == 'abc**'     # Python 2.4
        raises(TypeError, 'abc'.ljust, 6, '')

    def test_replace(self):
        assert 'one!two!three!'.replace('!', '@', 1) == 'one@two!three!'
        assert 'one!two!three!'.replace('!', '') == 'onetwothree'
        assert 'one!two!three!'.replace('!', '@', 2) == 'one@two@three!'
        assert 'one!two!three!'.replace('!', '@', 3) == 'one@two@three@'
        assert 'one!two!three!'.replace('!', '@', 4) == 'one@two@three@'
        assert 'one!two!three!'.replace('!', '@', 0) == 'one!two!three!'
        assert 'one!two!three!'.replace('!', '@') == 'one@two@three@'
        assert 'one!two!three!'.replace('x', '@') == 'one!two!three!'
        assert 'one!two!three!'.replace('x', '@', 2) == 'one!two!three!'
        assert 'abc'.replace('', '-') == '-a-b-c-'
        assert 'abc'.replace('', '-', 3) == '-a-b-c'
        assert 'abc'.replace('', '-', 0) == 'abc'
        assert ''.replace('', '') == ''
        assert ''.replace('', 'a') == 'a'
        assert 'abc'.replace('ab', '--', 0) == 'abc'
        assert 'abc'.replace('xy', '--') == 'abc'
        assert '123'.replace('123', '') == ''
        assert '123123'.replace('123', '') == ''
        assert '123x123'.replace('123', '') == 'x'

    def test_replace_buffer(self):
        assert 'one'.replace(buffer('o'), buffer('n'), 1) == 'nne'
        assert 'one'.replace(buffer('o'), buffer('n')) == 'nne'

    def test_strip(self):
        s = " a b "
        assert s.strip() == "a b"
        assert s.rstrip() == " a b"
        assert s.lstrip() == "a b "
        assert 'xyzzyhelloxyzzy'.strip('xyz') == 'hello'
        assert 'xyzzyhelloxyzzy'.lstrip('xyz') == 'helloxyzzy'
        assert 'xyzzyhelloxyzzy'.rstrip('xyz') == 'xyzzyhello'

    def test_zfill(self):
        assert '123'.zfill(2) == '123'
        assert '123'.zfill(3) == '123'
        assert '123'.zfill(4) == '0123'
        assert '+123'.zfill(3) == '+123'
        assert '+123'.zfill(4) == '+123'
        assert '+123'.zfill(5) == '+0123'
        assert '-123'.zfill(3) == '-123'
        assert '-123'.zfill(4) == '-123'
        assert '-123'.zfill(5) == '-0123'
        assert ''.zfill(3) == '000'
        assert '34'.zfill(1) == '34'
        assert '34'.zfill(4) == '0034'
            
    def test_center(self):
        s="a b"
        assert s.center(0) == "a b"
        assert s.center(1) == "a b"
        assert s.center(2) == "a b"
        assert s.center(3) == "a b"
        assert s.center(4) == "a b "
        assert s.center(5) == " a b "
        assert s.center(6) == " a b  "
        assert s.center(7) == "  a b  "
        assert s.center(8) == "  a b   "
        assert s.center(9) == "   a b   "
        assert 'abc'.center(10) == '   abc    '
        assert 'abc'.center(6) == ' abc  '
        assert 'abc'.center(3) == 'abc'
        assert 'abc'.center(2) == 'abc'
        assert 'abc'.center(5, '*') == '*abc*'     # Python 2.4
        raises(TypeError, 'abc'.center, 4, 'cba')
        assert ' abc'.center(7) == '   abc '
        
    def test_count(self):
        assert "".count("x") ==0
        assert "".count("") ==1
        assert "Python".count("") ==7
        assert "ab aaba".count("ab") ==2
        assert 'aaa'.count('a') == 3
        assert 'aaa'.count('b') == 0
        assert 'aaa'.count('a', -1) == 1
        assert 'aaa'.count('a', -10) == 3
        assert 'aaa'.count('a', 0, -1) == 2
        assert 'aaa'.count('a', 0, -10) == 0
        assert 'ababa'.count('aba') == 1
     
    def test_startswith(self):
        assert 'ab'.startswith('ab') is True
        assert 'ab'.startswith('a') is True
        assert 'ab'.startswith('') is True
        assert 'x'.startswith('a') is False
        assert 'x'.startswith('x') is True
        assert ''.startswith('') is True
        assert ''.startswith('a') is False
        assert 'x'.startswith('xx') is False
        assert 'y'.startswith('xx') is False

    def test_startswith_more(self):
        assert 'ab'.startswith('a', 0) is True
        assert 'ab'.startswith('a', 1) is False
        assert 'ab'.startswith('b', 1) is True
        assert 'abc'.startswith('bc', 1, 2) is False
        assert 'abc'.startswith('c', -1, 4) is True

    def test_startswith_tuples(self):
        assert 'hello'.startswith(('he', 'ha'))
        assert not 'hello'.startswith(('lo', 'llo'))
        assert 'hello'.startswith(('hellox', 'hello'))
        assert not 'hello'.startswith(())
        assert 'helloworld'.startswith(('hellowo', 'rld', 'lowo'), 3)
        assert not 'helloworld'.startswith(('hellowo', 'ello', 'rld'), 3)
        assert 'hello'.startswith(('lo', 'he'), 0, -1)
        assert not 'hello'.startswith(('he', 'hel'), 0, 1)
        assert 'hello'.startswith(('he', 'hel'), 0, 2)
        raises(TypeError, 'hello'.startswith, (42,))
    
    def test_endswith(self):
        assert 'ab'.endswith('ab') is True
        assert 'ab'.endswith('b') is True
        assert 'ab'.endswith('') is True
        assert 'x'.endswith('a') is False
        assert 'x'.endswith('x') is True
        assert ''.endswith('') is True
        assert ''.endswith('a') is False
        assert 'x'.endswith('xx') is False
        assert 'y'.endswith('xx') is False

    def test_endswith_more(self):
        assert 'abc'.endswith('ab', 0, 2) is True
        assert 'abc'.endswith('bc', 1) is True
        assert 'abc'.endswith('bc', 2) is False
        assert 'abc'.endswith('b', -3, -1) is True

    def test_endswith_tuple(self):
        assert not 'hello'.endswith(('he', 'ha'))
        assert 'hello'.endswith(('lo', 'llo'))
        assert 'hello'.endswith(('hellox', 'hello'))
        assert not 'hello'.endswith(())
        assert 'helloworld'.endswith(('hellowo', 'rld', 'lowo'), 3)
        assert not 'helloworld'.endswith(('hellowo', 'ello', 'rld'), 3, -1)
        assert 'hello'.endswith(('hell', 'ell'), 0, -1)
        assert not 'hello'.endswith(('he', 'hel'), 0, 1)
        assert 'hello'.endswith(('he', 'hell'), 0, 4)
        raises(TypeError, 'hello'.endswith, (42,))

    def test_expandtabs(self):
        assert 'abc\rab\tdef\ng\thi'.expandtabs() ==    'abc\rab      def\ng       hi'
        assert 'abc\rab\tdef\ng\thi'.expandtabs(8) ==   'abc\rab      def\ng       hi'
        assert 'abc\rab\tdef\ng\thi'.expandtabs(4) ==   'abc\rab  def\ng   hi'
        assert 'abc\r\nab\tdef\ng\thi'.expandtabs(4) == 'abc\r\nab  def\ng   hi'
        assert 'abc\rab\tdef\ng\thi'.expandtabs() ==    'abc\rab      def\ng       hi'
        assert 'abc\rab\tdef\ng\thi'.expandtabs(8) ==   'abc\rab      def\ng       hi'
        assert 'abc\r\nab\r\ndef\ng\r\nhi'.expandtabs(4) == 'abc\r\nab\r\ndef\ng\r\nhi'

        s = 'xy\t'
        assert s.expandtabs() =='xy      '
        
        s = '\txy\t'
        assert s.expandtabs() =='        xy      '
        assert s.expandtabs(1) ==' xy '
        assert s.expandtabs(2) =='  xy  '
        assert s.expandtabs(3) =='   xy '
        
        assert 'xy'.expandtabs() =='xy'
        assert ''.expandtabs() ==''

    def test_expandtabs_overflows_gracefully(self):
        import sys
        if sys.maxint > (1 << 32):
            skip("Wrong platform")
        raises((MemoryError, OverflowError), 't\tt\t'.expandtabs, sys.maxint)

    def test_splitlines(self):
        s = ""
        assert s.splitlines() == []
        assert s.splitlines() == s.splitlines(1)
        s = "a + 4"
        assert s.splitlines() == ['a + 4']
        # The following is true if no newline in string.
        assert s.splitlines() == s.splitlines(1)
        s = "a + 4\nb + 2"
        assert s.splitlines() == ['a + 4', 'b + 2']
        assert s.splitlines(1) == ['a + 4\n', 'b + 2']
        s="ab\nab\n \n  x\n\n\n"
        assert s.splitlines() ==['ab',    'ab',  ' ',   '  x',   '',    '']
        assert s.splitlines() ==s.splitlines(0)
        assert s.splitlines(1) ==['ab\n', 'ab\n', ' \n', '  x\n', '\n', '\n']
        s="\none\n\two\nthree\n\n"
        assert s.splitlines() ==['', 'one', '\two', 'three', '']
        assert s.splitlines(1) ==['\n', 'one\n', '\two\n', 'three\n', '\n']
        # Split on \r and \r\n too
        assert '12\r34\r\n56'.splitlines() == ['12', '34', '56']
        assert '12\r34\r\n56'.splitlines(1) == ['12\r', '34\r\n', '56']
    
    def test_find(self):
        assert 'abcdefghiabc'.find('abc') == 0
        assert 'abcdefghiabc'.find('abc', 1) == 9
        assert 'abcdefghiabc'.find('def', 4) == -1
        assert 'abcdef'.find('', 13) == -1

    def test_index(self):
        from sys import maxint
        assert 'abcdefghiabc'.index('') == 0
        assert 'abcdefghiabc'.index('def') == 3
        assert 'abcdefghiabc'.index('abc') == 0
        assert 'abcdefghiabc'.index('abc', 1) == 9
        assert 'abcdefghiabc'.index('def', -4*maxint, 4*maxint) == 3
        raises(ValueError, 'abcdefghiabc'.index, 'hib')
        raises(ValueError, 'abcdefghiab'.index, 'abc', 1)
        raises(ValueError, 'abcdefghi'.index, 'ghi', 8)
        raises(ValueError, 'abcdefghi'.index, 'ghi', -1)
        raises(TypeError, 'abcdefghijklmn'.index, 'abc', 0, 0.0)
        raises(TypeError, 'abcdefghijklmn'.index, 'abc', -10.0, 30)

    def test_rfind(self):
        assert 'abc'.rfind('', 4) == -1
        assert 'abcdefghiabc'.rfind('abc') == 9
        assert 'abcdefghiabc'.rfind('') == 12
        assert 'abcdefghiabc'.rfind('abcd') == 0
        assert 'abcdefghiabc'.rfind('abcz') == -1
        assert 'abc'.rfind('', 0) == 3
        assert 'abc'.rfind('', 3) == 3

    def test_rindex(self):
        from sys import maxint
        assert 'abcdefghiabc'.rindex('') == 12
        assert 'abcdefghiabc'.rindex('def') == 3
        assert 'abcdefghiabc'.rindex('abc') == 9
        assert 'abcdefghiabc'.rindex('abc', 0, -1) == 0
        assert 'abcdefghiabc'.rindex('abc', -4*maxint, 4*maxint) == 9
        raises(ValueError, 'abcdefghiabc'.rindex, 'hib')
        raises(ValueError, 'defghiabc'.rindex, 'def', 1)
        raises(ValueError, 'defghiabc'.rindex, 'abc', 0, -1)
        raises(ValueError, 'abcdefghi'.rindex, 'ghi', 0, 8)
        raises(ValueError, 'abcdefghi'.rindex, 'ghi', 0, -1)
        raises(TypeError, 'abcdefghijklmn'.rindex, 'abc', 0, 0.0)
        raises(TypeError, 'abcdefghijklmn'.rindex, 'abc', -10.0, 30)


    def test_partition(self):

        assert ('this is the par', 'ti', 'tion method') == \
            'this is the partition method'.partition('ti')

        # from raymond's original specification
        S = 'http://www.python.org'
        assert ('http', '://', 'www.python.org') == S.partition('://')
        assert ('http://www.python.org', '', '') == S.partition('?')
        assert ('', 'http://', 'www.python.org') == S.partition('http://')
        assert ('http://www.python.', 'org', '') == S.partition('org')

        raises(ValueError, S.partition, '')
        raises(TypeError, S.partition, None)

    def test_rpartition(self):

        assert ('this is the rparti', 'ti', 'on method') == \
            'this is the rpartition method'.rpartition('ti')

        # from raymond's original specification
        S = 'http://www.python.org'
        assert ('http', '://', 'www.python.org') == S.rpartition('://')
        assert ('', '', 'http://www.python.org') == S.rpartition('?')
        assert ('', 'http://', 'www.python.org') == S.rpartition('http://')
        assert ('http://www.python.', 'org', '') == S.rpartition('org')

        raises(ValueError, S.rpartition, '')
        raises(TypeError, S.rpartition, None)

    def test_split_maxsplit(self):
        assert "/a/b/c".split('/', 2) == ['','a','b/c']
        assert "a/b/c".split("/") == ['a', 'b', 'c']
        assert " a ".split(None, 0) == ['a ']
        assert " a ".split(None, 1) == ['a']
        assert " a a ".split(" ", 0) == [' a a ']
        assert " a a ".split(" ", 1) == ['', 'a a ']

    def test_join(self):
        assert ", ".join(['a', 'b', 'c']) == "a, b, c"
        assert "".join([]) == ""
        assert "-".join(['a', 'b']) == 'a-b'
        raises(TypeError, ''.join, 1)
        raises(TypeError, ''.join, [1])
        raises(TypeError, ''.join, [[1]])

    def test_unicode_join_endcase(self):
        # This class inserts a Unicode object into its argument's natural
        # iteration, in the 3rd position.
        class OhPhooey(object):
            def __init__(self, seq):
                self.it = iter(seq)
                self.i = 0

            def __iter__(self):
                return self

            def next(self):
                i = self.i
                self.i = i+1
                if i == 2:
                    return unicode("fooled you!")
                return self.it.next()
            
        f = ('a\n', 'b\n', 'c\n')
        got = " - ".join(OhPhooey(f))
        assert got == unicode("a\n - b\n - fooled you! - c\n")

    def test_lower(self):
        assert "aaa AAA".lower() == "aaa aaa"
        assert "".lower() == ""

    def test_upper(self):
        assert "aaa AAA".upper() == "AAA AAA"
        assert "".upper() == ""

    def test_isalnum(self):
        assert "".isalnum() == False
        assert "!Bro12345w&&&&n Fox".isalnum() == False
        assert "125 Brown Foxes".isalnum() == False
        assert "125BrownFoxes".isalnum() == True

    def test_isalpha(self):
        assert "".isalpha() == False
        assert "!Bro12345w&&&&nFox".isalpha() == False
        assert "Brown Foxes".isalpha() == False
        assert "125".isalpha() == False

    def test_isdigit(self):
        assert "".isdigit() == False
        assert "!Bro12345w&&&&nFox".isdigit() == False
        assert "Brown Foxes".isdigit() == False
        assert "125".isdigit() == True

    def test_isspace(self):
        assert "".isspace() == False
        assert "!Bro12345w&&&&nFox".isspace() == False
        assert " ".isspace() ==  True
        assert "\t\t\b\b\n".isspace() == False
        assert "\t\t".isspace() == True
        assert "\t\t\r\r\n".isspace() == True
        
    def test_islower(self):
        assert "".islower() == False
        assert " ".islower() ==  False
        assert "\t\t\b\b\n".islower() == False
        assert "b".islower() == True
        assert "bbb".islower() == True
        assert "!bbb".islower() == True
        assert "BBB".islower() == False
        assert "bbbBBB".islower() == False

    def test_isupper(self):
        assert "".isupper() == False
        assert " ".isupper() ==  False
        assert "\t\t\b\b\n".isupper() == False
        assert "B".isupper() == True
        assert "BBB".isupper() == True
        assert "!BBB".isupper() == True
        assert "bbb".isupper() == False
        assert "BBBbbb".isupper() == False
                          
         
    def test_swapcase(self):
        assert "aaa AAA 111".swapcase() == "AAA aaa 111"
        assert "".swapcase() == ""

    def test_translate(self):
        def maketrans(origin, image):
            if len(origin) != len(image):
                raise ValueError("maketrans arguments must have same length")
            L = [chr(i) for i in range(256)]
            for i in range(len(origin)):
                L[ord(origin[i])] = image[i]

            tbl = ''.join(L)
            return tbl
        
        table = maketrans('abc', 'xyz')
        assert 'xyzxyz' == 'xyzabcdef'.translate(table, 'def')

        table = maketrans('a', 'A')
        assert 'Abc' == 'abc'.translate(table)
        assert 'xyz' == 'xyz'.translate(table)
        assert 'yz' ==  'xyz'.translate(table, 'x')
        
        raises(ValueError, 'xyz'.translate, 'too short', 'strip')
        raises(ValueError, 'xyz'.translate, 'too short')
        raises(ValueError, 'xyz'.translate, 'too long'*33)

    def test_iter(self):
        l=[]
        for i in iter("42"):
            l.append(i)
        assert l == ['4','2']
        
    def test_repr(self):
        assert repr("")       =="''"
        assert repr("a")      =="'a'"
        assert repr("'")      =='"\'"'
        assert repr("\'")     =="\"\'\""
        assert repr("\"")     =='\'"\''
        assert repr("\t")     =="'\\t'"
        assert repr("\\")     =="'\\\\'"
        assert repr('')       =="''"
        assert repr('a')      =="'a'"
        assert repr('"')      =="'\"'"
        assert repr('\'')     =='"\'"'
        assert repr('\"')     =="'\"'"
        assert repr('\t')     =="'\\t'"
        assert repr('\\')     =="'\\\\'"
        assert repr("'''\"")  =='\'\\\'\\\'\\\'"\''
        assert repr(chr(19))  =="'\\x13'"
        assert repr(chr(2))   =="'\\x02'"

    def test_contains(self):
        assert '' in 'abc'
        assert 'a' in 'abc'
        assert 'ab' in 'abc'
        assert not 'd' in 'abc'
        raises(TypeError, 'a'.__contains__, 1)

    def test_decode(self):
        assert 'hello'.decode('rot-13') == 'uryyb'
        assert 'hello'.decode('string-escape') == 'hello'
        assert u'hello'.decode('rot-13') == 'uryyb'

    def test_encode(self):
        assert 'hello'.encode() == 'hello'
        assert type('hello'.encode()) is str
        
    def test_hash(self):
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        assert hash('hello') & 0x7fffffff == 0x347697fd
        assert hash('hello world!') & 0x7fffffff == 0x2f0bb411

    def test_buffer(self):
        x = "he"
        x += "llo"
        b = buffer(x)
        assert len(b) == 5
        assert b[-1] == "o"
        assert b[:] == "hello"
        raises(TypeError, "b[3] = 'x'")

    def test_getnewargs(self):
        assert  "foo".__getnewargs__() == ("foo",)

    def test_subclass(self):
        class S(str):
            pass
        s = S('abc')
        assert type(''.join([s])) is str
        assert type(s.join([])) is str
        assert type(s.split('x')[0]) is str
        assert type(s.ljust(3)) is str
        assert type(s.rjust(3)) is str
        assert type(S('A').upper()) is str
        assert type(S('a').lower()) is str
        assert type(S('A').capitalize()) is str
        assert type(S('A').title()) is str
        assert type(s.replace(s, s)) is str
        assert type(s.replace('x', 'y')) is str
        assert type(s.replace('x', 'y', 0)) is str
        assert type(s.zfill(3)) is str
        assert type(s.strip()) is str
        assert type(s.rstrip()) is str
        assert type(s.lstrip()) is str
        assert type(s.center(3)) is str
        assert type(s.splitlines()[0]) is str

    def test_str_unicode_interchangeable(self):
        stuff = ['xxxxx', u'xxxxx']
        for x in stuff:
            for y in stuff:
                assert x.startswith(y)
                assert x.endswith(y)
                assert x.count(y) == 1
                assert x.find(y) != -1
                assert x.index(y) == 0
                d = ["x", u"x"]
                for a in d:
                    for b in d:
                        assert x.replace(a, b) == y
                assert x.rfind(y) != -1
                assert x.rindex(y) == 0
                assert x.split(y) == ['', '']
                assert x.rsplit(y) == ['', '']
                assert x.strip(y) == ''
                assert x.rstrip(y) == ''
                assert x.lstrip(y) == ''

    def test_replace_overflow(self):
        import sys
        if sys.maxint > 2**31-1:
            skip("Wrong platform")
        s = "a" * (2**16)
        raises(OverflowError, s.replace, "", s)

    def test_getslice(self):
        assert "foobar".__getslice__(4, 4321) == "ar"
        s = "abc"
        assert s[:] == "abc"
        assert s[1:] == "bc"
        assert s[:2] == "ab"
        assert s[1:2] == "b"
        assert s[-2:] == "bc"
        assert s[:-1] == "ab"
        assert s[-2:2] == "b"
        assert s[1:-1] == "b"
        assert s[-2:-1] == "b"

    def test_no_len_on_str_iter(self):
        iterable = "hello"
        raises(TypeError, len, iter(iterable))

    def test_overflow_replace(self):
        import sys
        if sys.maxint > 2**31-1:
            skip("Wrong platform")
        x = "A" * (2**16)
        raises(OverflowError, x.replace, '', x)

class AppTestPrebuilt(AppTestStringObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withprebuiltchar": True})

class AppTestShare(AppTestStringObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.sharesmallstr": True})

class AppTestPrebuiltShare(AppTestStringObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withprebuiltchar": True,
                                       "objspace.std.sharesmallstr": True})
