# -*- encoding: utf-8 -*-
import py
import sys


class TestUnicodeObject:
    spaceconfig = dict(usemodules=('unicodedata',))

    def test_unicode_to_decimal_w(self, space):
        from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
        w_s = space.wrap(u"\N{EM SPACE}-3\N{EN SPACE}")
        s2 = unicode_to_decimal_w(space, w_s)
        assert s2 == " -3 "

    @py.test.mark.skipif("not config.option.runappdirect and sys.maxunicode == 0xffff")
    def test_unicode_to_decimal_w_wide(self, space):
        from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
        w_s = space.wrap(u'\U0001D7CF\U0001D7CE') # 𝟏𝟎
        s2 = unicode_to_decimal_w(space, w_s)
        assert s2 == "10"

    def test_listview_unicode(self):
        w_str = self.space.wrap(u'abcd')
        assert self.space.listview_unicode(w_str) == list(u"abcd")

    def test_new_shortcut(self):
        space = self.space
        w_uni = self.space.wrap(u'abcd')
        w_new = space.call_method(
                space.w_unicode, "__new__", space.w_unicode, w_uni)
        assert w_new is w_uni


class AppTestUnicodeStringStdOnly:
    def test_compares(self):
        assert type('a') != type(b'a')
        assert 'a' != b'a'
        assert b'a' != 'a'
        assert not ('a' == 5)
        assert 'a' != 5
        raises(TypeError, "'a' < 5")
        

class AppTestUnicodeString:
    spaceconfig = dict(usemodules=('unicodedata',))

    def test_addition(self):
        import operator
        assert 'a' + 'b' == 'ab'
        raises(TypeError, operator.add, b'a', 'b')

    def test_join(self):
        def check(a, b):
            assert a == b
            assert type(a) == type(b)
        check(', '.join(['a']), 'a')
        raises(TypeError, ','.join, [b'a']) 
        exc = raises(TypeError, ''.join, ['a', 2, 3])
        assert 'sequence item 1' in str(exc.value)

    def test_contains(self):
        assert '' in 'abc'
        assert 'a' in 'abc'
        assert 'bc' in 'abc'
        assert '\xe2' in 'g\xe2teau'

    def test_splitlines(self):
        assert ''.splitlines() == []
        assert ''.splitlines(1) == []
        assert '\n'.splitlines() == ['']
        assert 'a'.splitlines() == ['a']
        assert 'one\ntwo'.splitlines() == ['one', 'two']
        assert '\ntwo\nthree'.splitlines() == ['', 'two', 'three']
        assert '\n\n'.splitlines() == ['', '']
        assert 'a\nb\nc'.splitlines(1) == ['a\n', 'b\n', 'c']
        assert '\na\nb\n'.splitlines(1) == ['\n', 'a\n', 'b\n']

    def test_zfill(self):
        assert '123'.zfill(2) == '123'
        assert '123'.zfill(3) == '123'
        assert '123'.zfill(4) == '0123'
        assert '123'.zfill(6) == '000123'
        assert '+123'.zfill(2) == '+123'
        assert '+123'.zfill(3) == '+123'
        assert '+123'.zfill(4) == '+123'
        assert '+123'.zfill(5) == '+0123'
        assert '+123'.zfill(6) == '+00123'
        assert '-123'.zfill(3) == '-123'
        assert '-123'.zfill(4) == '-123'
        assert '-123'.zfill(5) == '-0123'
        assert ''.zfill(3) == '000'
        assert '34'.zfill(1) == '34'
        assert '34'.zfill(4) == '0034'

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
        assert 'a|b|c|d'.split('|') == ['a', 'b', 'c', 'd']
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
        raises(ValueError, 'abc'.split, '')
        raises(ValueError, 'abc'.split, '')
        assert '   a b c d'.split(None, 0) == ['a b c d']

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
        assert 'a|b|c|d'.rsplit('|') == ['a', 'b', 'c', 'd']
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
        raises(ValueError, 'abc'.rsplit, '')
        raises(ValueError, 'abc'.rsplit, '')
        assert '  a b c  '.rsplit(None, 0) == ['  a b c']
        assert ''.rsplit('aaa') == ['']

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
        assert 'abc'.center(5, '*') == '*abc*'    # Python 2.4
        assert 'abc'.center(5, '*') == '*abc*'     # Python 2.4
        raises(TypeError, 'abc'.center, 4, 'cba')

    def test_title(self):
        assert "brown fox".title() == "Brown Fox"
        assert "!brown fox".title() == "!Brown Fox"
        assert "bROWN fOX".title() == "Brown Fox"
        assert "Brown Fox".title() == "Brown Fox"
        assert "bro!wn fox".title() == "Bro!Wn Fox"
        assert u'A\u03a3 \u1fa1xy'.title() == u'A\u03c2 \u1fa9xy'
        assert u'A\u03a3A'.title() == u'A\u03c3a'

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
        assert '\u1FFc'.istitle()
        assert 'Greek \u1FFcitlecases ...'.istitle()

    def test_islower_isupper_with_titlecase(self):
        # \u01c5 is a char which is neither lowercase nor uppercase, but
        # titlecase
        assert not '\u01c5abc'.islower()
        assert not '\u01c5ABC'.isupper()

    def test_islower(self):
        assert u'\u2177'.islower()

    def test_isidentifier(self):
        assert "".isidentifier() is False
        assert "a4".isidentifier() is True
        assert "_var".isidentifier() is True
        assert "_!var".isidentifier() is False
        assert "3abc".isidentifier() is False
        
    def test_capitalize(self):
        assert "brown fox".capitalize() == "Brown fox"
        assert ' hello '.capitalize() == ' hello '
        assert 'Hello '.capitalize() == 'Hello '
        assert 'hello '.capitalize() == 'Hello '
        assert 'aaaa'.capitalize() == 'Aaaa'
        assert 'AaAa'.capitalize() == 'Aaaa'
        # check that titlecased chars are lowered correctly
        # \u1ffc is the titlecased char
        assert ('\u1ff3\u1ff3\u1ffc\u1ffc'.capitalize() ==
                '\u03a9\u0399\u1ff3\u1ff3\u1ff3')
        # check with cased non-letter chars
        assert ('\u24c5\u24ce\u24c9\u24bd\u24c4\u24c3'.capitalize() ==
                '\u24c5\u24e8\u24e3\u24d7\u24de\u24dd')
        assert ('\u24df\u24e8\u24e3\u24d7\u24de\u24dd'.capitalize() ==
                '\u24c5\u24e8\u24e3\u24d7\u24de\u24dd')
        assert '\u2160\u2161\u2162'.capitalize() == '\u2160\u2171\u2172'
        assert '\u2170\u2171\u2172'.capitalize() == '\u2160\u2171\u2172'
        # check with Ll chars with no upper - nothing changes here
        assert ('\u019b\u1d00\u1d86\u0221\u1fb7'.capitalize() ==
                '\u019b\u1d00\u1d86\u0221\u1fb7')

    def test_isprintable(self):
        assert "".isprintable()
        assert " ".isprintable()
        assert "abcdefg".isprintable()
        assert not "abcdefg\n".isprintable()
        # some defined Unicode character
        assert "\u0374".isprintable()
        # undefined character
        assert not "\u0378".isprintable()
        # single surrogate character
        assert not "\ud800".isprintable()

    @py.test.mark.skipif("not config.option.runappdirect and sys.maxunicode == 0xffff")
    def test_isprintable_wide(self):
        assert '\U0001F46F'.isprintable()  # Since unicode 6.0
        assert not '\U000E0020'.isprintable()

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
        assert 'abc'.rjust(5, '*') == '**abc'    # Python 2.4
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
        assert 'abc'.ljust(5, '*') == 'abc**'    # Python 2.4
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

    def test_replace_overflow(self):
        import sys
        if sys.maxsize > 2**31-1:
            skip("Wrong platform")
        s = "a" * (2**16)
        raises(OverflowError, s.replace, "", s)

    def test_strip(self):
        s = " a b "
        assert s.strip() == "a b"
        assert s.rstrip() == " a b"
        assert s.lstrip() == "a b "
        assert 'xyzzyhelloxyzzy'.strip('xyz') == 'hello'
        assert 'xyzzyhelloxyzzy'.lstrip('xyz') == 'helloxyzzy'
        assert 'xyzzyhelloxyzzy'.rstrip('xyz') == 'xyzzyhello'

    def test_long_from_unicode(self):
        assert int('12345678901234567890') == 12345678901234567890
        assert int('123', 7) == 66

    def test_int_from_unicode(self):
        assert int('12345') == 12345

    def test_float_from_unicode(self):
        assert float('123.456e89') == float('123.456e89')

    def test_repr_16bits(self):
        # this used to fail when run on a CPython host with 16-bit unicodes
        s = repr('\U00101234')
        assert s == "'\\U00101234'"

    def test_repr(self):
        for ustr in ["", "a", "'", "\'", "\"", "\t", "\\", '',
                     'a', '"', '\'', '\"', '\t', '\\', "'''\"",
                     chr(19), chr(2), '\u1234', '\U00101234']:
            assert eval(repr(ustr)) == ustr

    def test_getnewargs(self):
        class X(str):
            pass
        x = X("foo\u1234")
        a = x.__getnewargs__()
        assert a == ("foo\u1234",)
        assert type(a[0]) is str

    def test_call_unicode(self):
        assert str() == ''
        assert str(None) == 'None'
        assert str(123) == '123'
        assert str(object=123) == '123'
        assert str([2, 3]) == '[2, 3]'
        assert str(errors='strict') == ''
        class U(str):
            pass
        assert str(U()).__class__ is str
        assert U().__str__().__class__ is str
        assert U('test') == 'test'
        assert U('test').__class__ is U
        assert U(errors='strict') == U('')

    def test_call_unicode_2(self):
        class X(object):
            def __bytes__(self):
                return b'x'
        raises(TypeError, str, X(), 'ascii')

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
        try:
            'hello'.startswith(['o'])
        except TypeError as e:
            msg = str(e)
            assert 'str' in msg
            assert 'tuple' in msg
        else:
            assert False, 'Expected TypeError'

    def test_startswith_too_large(self):
        assert u'ab'.startswith(u'b', 1) is True
        assert u'ab'.startswith(u'', 2) is True
        assert u'ab'.startswith(u'', 3) is True   # not False
        assert u'ab'.endswith(u'b', 1) is True
        assert u'ab'.endswith(u'', 2) is True
        assert u'ab'.endswith(u'', 3) is True   # not False

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

    def test_startswith_endswith_convert(self):
        assert 'hello'.startswith(('he\u1111', 'he'))
        assert not 'hello'.startswith(('lo\u1111', 'llo'))
        assert 'hello'.startswith(('hellox\u1111', 'hello'))
        assert not 'hello'.startswith(('lo', 'he\u1111'), 0, -1)
        assert not 'hello'.endswith(('he\u1111', 'he'))
        assert 'hello'.endswith(('\u1111lo', 'llo'))
        assert 'hello'.endswith(('\u1111hellox', 'hello'))

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
        try:
            'hello'.endswith(['o'])
        except TypeError as e:
            msg = str(e)
            assert 'str' in msg
            assert 'tuple' in msg
        else:
            assert False, 'Expected TypeError'

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
        if sys.maxsize > (1 << 32):
            skip("Wrong platform")
        raises((OverflowError, MemoryError), 't\tt\t'.expandtabs, sys.maxsize)

    def test_expandtabs_0(self):
        assert u'x\ty'.expandtabs(0) == u'xy'
        assert u'x\ty'.expandtabs(-42) == u'xy'

    def test_translate(self):
        assert 'bbbc' == 'abababc'.translate({ord('a'):None})
        assert 'iiic' == 'abababc'.translate({ord('a'):None, ord('b'):ord('i')})
        assert 'iiix' == 'abababc'.translate({ord('a'):None, ord('b'):ord('i'), ord('c'):'x'})
        assert '<i><i><i>c' == 'abababc'.translate({ord('a'):None, ord('b'):'<i>'})
        assert 'c' == 'abababc'.translate({ord('a'):None, ord('b'):''})
        assert 'xyyx' == 'xzx'.translate({ord('z'):'yy'})
        assert 'abcd' == 'ab\0d'.translate('c')
        assert 'abcd' == 'abcd'.translate('')
        assert 'abababc'.translate({ord('a'): ''}) == 'bbbc'

        raises(TypeError, 'hello'.translate)

    def test_maketrans(self):
        assert 'abababc' == 'abababc'.translate({'b': '<i>'})
        tbl = str.maketrans({'a': None, 'b': '<i>'})
        assert '<i><i><i>c' == 'abababc'.translate(tbl)
        tbl = str.maketrans('abc', 'xyz', 'd')
        assert 'xyzzy' == 'abdcdcbdddd'.translate(tbl)

        raises(TypeError, str.maketrans)
        raises(ValueError, str.maketrans, 'abc', 'defg')
        raises(TypeError, str.maketrans, 2, 'def')
        raises(TypeError, str.maketrans, 'abc', 2)
        raises(TypeError, str.maketrans, 'abc', 'def', 2)
        raises(ValueError, str.maketrans, {'xy': 2})
        raises(TypeError, str.maketrans, {(1,): 2})

        raises(TypeError, 'hello'.translate)
        raises(TypeError, 'abababc'.translate, 'abc', 'xyz')

    def test_unicode_form_encoded_object(self):
        assert str(b'x', 'utf-8') == 'x'
        assert str(b'x', 'utf-8', 'strict') == 'x'

    def test_unicode_startswith_tuple(self):
        assert 'xxx'.startswith(('x', 'y', 'z'), 0)
        assert 'xxx'.endswith(('x', 'y', 'z'), 0)

    def test_missing_cases(self):
        # some random cases, which are discovered to not be tested during annotation
        assert 'xxx'[1:1] == ''

    # these tests test lots of encodings, so they really belong to the _codecs
    # module. however, they test useful unicode methods too
    # they are stolen from CPython's unit tests

    def test_codecs_utf7(self):
        utfTests = [
            ('A\u2262\u0391.', b'A+ImIDkQ.'),             # RFC2152 example
            ('Hi Mom -\u263a-!', b'Hi Mom -+Jjo--!'),     # RFC2152 example
            ('\u65E5\u672C\u8A9E', b'+ZeVnLIqe-'),        # RFC2152 example
            ('Item 3 is \u00a31.', b'Item 3 is +AKM-1.'), # RFC2152 example
            ('+', b'+-'),
            ('+-', b'+--'),
            ('+?', b'+-?'),
            ('\?', b'+AFw?'),
            ('+?', b'+-?'),
            (r'\\?', b'+AFwAXA?'),
            (r'\\\?', b'+AFwAXABc?'),
            (r'++--', b'+-+---'),
        ]

        for (x, y) in utfTests:
            assert x.encode('utf-7') == y

        # surrogates are supported
        assert str(b'+3ADYAA-', 'utf-7') == '\udc00\ud800'

        assert str(b'+AB', 'utf-7', 'replace') == '\ufffd'

    def test_codecs_utf8(self):
        import sys
        assert ''.encode('utf-8') == b''
        assert '\u20ac'.encode('utf-8') == b'\xe2\x82\xac'
        raises(UnicodeEncodeError, '\ud800'.encode, 'utf-8')
        raises(UnicodeEncodeError, '\udc00'.encode, 'utf-8')
        raises(UnicodeEncodeError, '\udc00!'.encode, 'utf-8')
        if sys.maxunicode > 0xFFFF and len(chr(0x10000)) == 1:
            raises(UnicodeEncodeError, '\ud800\udc02'.encode, 'utf-8')
            raises(UnicodeEncodeError, '\ud84d\udc56'.encode, 'utf-8')
            raises(UnicodeEncodeError, ('\ud800\udc02'*1000).encode, 'utf-8')
        else:
            assert '\ud800\udc02'.encode('utf-8') == b'\xf0\x90\x80\x82'
            assert '\ud84d\udc56'.encode('utf-8') == b'\xf0\xa3\x91\x96'
            assert ('\ud800\udc02'*1000).encode('utf-8') == b'\xf0\x90\x80\x82'*1000
        assert (
            '\u6b63\u78ba\u306b\u8a00\u3046\u3068\u7ffb\u8a33\u306f'
            '\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002\u4e00'
            '\u90e8\u306f\u30c9\u30a4\u30c4\u8a9e\u3067\u3059\u304c'
            '\u3001\u3042\u3068\u306f\u3067\u305f\u3089\u3081\u3067'
            '\u3059\u3002\u5b9f\u969b\u306b\u306f\u300cWenn ist das'
            ' Nunstuck git und'.encode('utf-8') == 
            b'\xe6\xad\xa3\xe7\xa2\xba\xe3\x81\xab\xe8\xa8\x80\xe3\x81'
            b'\x86\xe3\x81\xa8\xe7\xbf\xbb\xe8\xa8\xb3\xe3\x81\xaf\xe3'
            b'\x81\x95\xe3\x82\x8c\xe3\x81\xa6\xe3\x81\x84\xe3\x81\xbe'
            b'\xe3\x81\x9b\xe3\x82\x93\xe3\x80\x82\xe4\xb8\x80\xe9\x83'
            b'\xa8\xe3\x81\xaf\xe3\x83\x89\xe3\x82\xa4\xe3\x83\x84\xe8'
            b'\xaa\x9e\xe3\x81\xa7\xe3\x81\x99\xe3\x81\x8c\xe3\x80\x81'
            b'\xe3\x81\x82\xe3\x81\xa8\xe3\x81\xaf\xe3\x81\xa7\xe3\x81'
            b'\x9f\xe3\x82\x89\xe3\x82\x81\xe3\x81\xa7\xe3\x81\x99\xe3'
            b'\x80\x82\xe5\xae\x9f\xe9\x9a\x9b\xe3\x81\xab\xe3\x81\xaf'
            b'\xe3\x80\x8cWenn ist das Nunstuck git und'
        )

        # UTF-8 specific decoding tests
        assert str(b'\xf0\xa3\x91\x96', 'utf-8') == '\U00023456' 
        assert str(b'\xf0\x90\x80\x82', 'utf-8') == '\U00010002' 
        assert str(b'\xe2\x82\xac', 'utf-8') == '\u20ac' 
        # Invalid Continuation Bytes, EOF
        raises(UnicodeDecodeError, b'\xc4\x00'.decode, 'utf-8')
        raises(UnicodeDecodeError, b'\xe2\x82'.decode, 'utf-8')
        # Non-Canonical Forms
        raises(UnicodeDecodeError, b'\xc0\x80'.decode, 'utf-8')
        raises(UnicodeDecodeError, b'\xc1\xbf'.decode, 'utf-8')
        raises(UnicodeDecodeError, b'\xe0\x9f\xbf'.decode, 'utf-8')
        raises(UnicodeDecodeError, b'\xf0\x8f\x8f\x84'.decode, 'utf-8')
        raises(UnicodeDecodeError, b'\xf5\x80\x81\x82'.decode, 'utf-8')
        raises(UnicodeDecodeError, b'\xf4\x90\x80\x80'.decode, 'utf-8')
        # CESU-8
        raises(UnicodeDecodeError, b'\xed\xa0\xbc\xed\xb2\xb1'.decode, 'utf-8') 

    def test_codecs_errors(self):
        # Error handling (encoding)
        raises(UnicodeError, 'Andr\202 x'.encode, 'ascii')
        raises(UnicodeError, 'Andr\202 x'.encode, 'ascii','strict')
        assert 'Andr\202 x'.encode('ascii','ignore') == b"Andr x"
        assert 'Andr\202 x'.encode('ascii','replace') == b"Andr? x"

        # Error handling (decoding)
        raises(UnicodeError, str, b'Andr\202 x', 'ascii')
        raises(UnicodeError, str, b'Andr\202 x', 'ascii','strict')
        assert str(b'Andr\202 x','ascii','ignore') == "Andr x"
        assert str(b'Andr\202 x','ascii','replace') == 'Andr\uFFFD x'

        # Error handling (unknown character names)
        assert b"\\N{foo}xx".decode("unicode-escape", "ignore") == "xx"

        # Error handling (truncated escape sequence)
        raises(UnicodeError, b"\\".decode, "unicode-escape")

        raises(UnicodeError, b"\xc2".decode, "utf-8")
        assert b'\xe1\x80'.decode('utf-8', 'replace') == "\ufffd"

    def test_repr_printable(self):
        # PEP 3138: __repr__ respects printable characters.
        x = '\u027d'
        y = "'\u027d'"
        assert (repr(x) == y)
        x = '\U00090418\u027d\U000582b9\u54c3\U000fcb6e'
        y = "'\\U00090418\u027d\\U000582b9\u54c3\\U000fcb6e'"
        assert (repr(x) == y)
        assert (repr('\n') == 
                "'\\n'")


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

    def test_mul(self):
        zero = 0
        assert type('' * zero) == type(zero * '') is str
        assert '' * zero == zero * '' == ''
        assert 'x' * zero == zero * 'x' == ''
        assert type('x' * zero) == type(zero * 'x') is str
        assert '123' * zero == zero * '123' == ''
        assert type('123' * zero) == type(zero * '123') is str
        for i in range(10):
            u = '123' * i
            assert len(u) == 3*i
            for j in range(0, i, 3):
                assert u[j+0] == '1'
                assert u[j+1] == '2'
                assert u[j+2] == '3'
            assert '123' * i == i * '123'

    def test_index(self):
        assert "rrarrrrrrrrra".index('a', 4, None) == 12
        assert "rrarrrrrrrrra".index('a', None, 6) == 2

    def test_rindex(self):
        from sys import maxsize
        assert 'abcdefghiabc'.rindex('') == 12
        assert 'abcdefghiabc'.rindex('def') == 3
        assert 'abcdefghiabc'.rindex('abc') == 9
        assert 'abcdefghiabc'.rindex('abc', 0, -1) == 0
        assert 'abcdefghiabc'.rindex('abc', -4*maxsize, 4*maxsize) == 9
        assert 'rrarrrrrrrrra'.rindex('a', 4, None) == 12

        raises(ValueError, 'abcdefghiabc'.rindex, 'hib')
        raises(ValueError, 'defghiabc'.rindex, 'def', 1)
        raises(ValueError, 'defghiabc'.rindex, 'abc', 0, -1)
        raises(ValueError, 'abcdefghi'.rindex, 'ghi', 0, 8)
        raises(ValueError, 'abcdefghi'.rindex, 'ghi', 0, -1)
        raises(TypeError, 'abcdefghijklmn'.rindex, 'abc', 0, 0.0)
        raises(TypeError, 'abcdefghijklmn'.rindex, 'abc', -10.0, 30)

    def test_rfind(self):
        assert 'abcdefghiabc'.rfind('abc') == 9
        assert 'abcdefghiabc'.rfind('') == 12
        assert 'abcdefghiabc'.rfind('abcd') == 0
        assert 'abcdefghiabc'.rfind('abcz') == -1

    def test_rfind_corner_case(self):
        assert 'abc'.rfind('', 4) == -1

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

    def test_swapcase(self):
        assert '\xe4\xc4\xdf'.swapcase() == '\xc4\xe4SS'
        assert u'\u0345\u03a3'.swapcase() == u'\u0399\u03c3'

    def test_call_special_methods(self):
        # xxx not completely clear if these are implementation details or not
        assert 'abc'.__add__('def') == 'abcdef'
        assert 'abc'.__add__('def') == 'abcdef'
        assert 'abc'.__add__('def') == 'abcdef'
        # xxx CPython has no str.__radd__ and no unicode.__radd__

    def test_str_unicode_concat_overrides(self):
        "Test from Jython about being bug-compatible with CPython."

        def check(value, expected):
            assert type(value) == type(expected)
            assert value == expected

        def _test_concat(t1, t2):
            class SubclassB(t2):
                def __add__(self, other):
                    return SubclassB(t2(self) + t2(other))
            check(SubclassB('py') + SubclassB('thon'), SubclassB('python'))
            check(t1('python') + SubclassB('3'), str('python3'))
            check(SubclassB('py') + t1('py'), SubclassB('pypy'))

            class SubclassC(t2):
                def __radd__(self, other):
                    return SubclassC(t2(other) + t2(self))
            check(SubclassC('stack') + SubclassC('less'), t2('stackless'))
            check(t1('iron') + SubclassC('python'), SubclassC('ironpython'))
            check(SubclassC('tiny') + t1('py'), str('tinypy'))

            class SubclassD(t2):
                def __add__(self, other):
                    return SubclassD(t2(self) + t2(other))

                def __radd__(self, other):
                    return SubclassD(t2(other) + t2(self))
            check(SubclassD('di') + SubclassD('ct'), SubclassD('dict'))
            check(t1('list') + SubclassD(' comp'), SubclassD('list comp'))
            check(SubclassD('dun') + t1('der'), SubclassD('dunder'))

        _test_concat(str, str)

    def test_returns_subclass(self):
        class X(str):
            pass

        class Y(str):
            def __str__(self):
                return X("stuff")

        assert str(Y()).__class__ is X

    def test_getslice(self):
        assert '123456'[1:5] == '2345'
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

    def test_iter(self):
        foo = "\u1111\u2222\u3333"
        assert hasattr(foo, '__iter__')
        iter = foo.__iter__()
        assert next(iter) == '\u1111'
        assert next(iter) == '\u2222'

    def test_no_len_on_str_iter(self):
        iterable = "hello"
        raises(TypeError, len, iter(iterable))

    def test_encode_raw_unicode_escape(self):
        u = str(b'\\', 'raw_unicode_escape')
        assert u == '\\'
        s = '\u05d1\u05d3\u05d9\u05e7\u05d4'.encode('raw_unicode_escape')
        assert s == b'\\u05d1\\u05d3\\u05d9\\u05e7\\u05d4'

    def test_decode_from_buffer(self):
        buf = b'character buffers are decoded to unicode'
        u = str(buf, 'utf-8', 'strict')
        assert u == 'character buffers are decoded to unicode'

    def test_unicode_conversion_with__str__(self):
        class A(str):
            def __str__(self):
                return "foo"
        class B(str):
            pass
        a = A('bar')
        assert a == 'bar'
        assert str(a) == 'foo'
        b = B('bar')
        assert b == 'bar'
        assert str(b) == 'bar'

    def test_unicode_conversion_with__str__(self):
        # new-style classes
        class A(object):
            def __str__(self):
                return '\u1234'
        s = str(A())
        assert type(s) is str
        assert s == '\u1234'
        # with old-style classes, it's different, but it should work as well
        class A:
            def __str__(self):
                return '\u1234'
        s = str(A())
        assert type(s) is str
        assert s == '\u1234'

    def test_formatting_unicode__str__(self):
        class A:
            def __init__(self, num):
                self.num = num
            def __str__(self):
                return chr(self.num)

        s = '%s' % A(111)    # this is ASCII
        assert type(s) is str
        assert s == chr(111)

        s = '%s' % A(0x1234)    # this is not ASCII
        assert type(s) is str
        assert s == '\u1234'

        # now the same with a new-style class...
        class A(object):
            def __init__(self, num):
                self.num = num
            def __str__(self):
                return chr(self.num)

        s = '%s' % A(111)    # this is ASCII
        assert type(s) is str
        assert s == chr(111)

        s = '%s' % A(0x1234)    # this is not ASCII
        assert type(s) is str
        assert s == '\u1234'

    def test_formatting_unicode__str__2(self):
        class A:
            def __str__(self):
                return 'baz'

        class B:
            def __str__(self):
                return 'bar'

        a = A()
        b = B()
        s = '%s %s' % (a, b)
        assert s == 'baz bar'

    def test_formatting_unicode__str__3(self):
        # "bah" is all I can say
        class X(object):
            def __repr__(self):
                return '\u1234'
        '%s' % X()
        #
        class X(object):
            def __str__(self):
                return '\u1234'
        '%s' % X()

    def test_formatting_unicode__repr__(self):
        # Printable character
        assert '%r' % chr(0xe9) == "'\xe9'"

    def test_str_subclass(self):
        class Foo9(str):
            def __str__(self):
                return "world"
        assert str(Foo9("hello")) == "world"

    def test_format_unicode_subclass(self):
        class U(str):
            def __str__(self):
                return '__str__ overridden'
        u = U('xxx')
        assert repr("%s" % u) == "'__str__ overridden'"
        assert repr("{}".format(u)) == "'__str__ overridden'"

    def test_format_c_overflow(self):
        import sys
        raises(OverflowError, u'{0:c}'.format, -1)
        raises(OverflowError, u'{0:c}'.format, sys.maxunicode + 1)

    def test_replace_with_buffer(self):
        raises(TypeError, 'abc'.replace, b'b', b'e')

    def test_unicode_subclass(self):
        class S(str):
            pass

        a = S('hello \u1234')
        b = str(a)
        assert type(b) is str
        assert b == 'hello \u1234'

        assert '%s' % S('mar\xe7') == 'mar\xe7'

    def test_format_new(self):
        assert '0{0}1{b}2'.format('A', b='B') == '0A1B2'

    def test_format_map(self):
        assert '0{a}1'.format_map({'a': 'A'}) == '0A1'

    def test_format_map_positional(self):
        raises(ValueError, '{}'.format_map, {})

    def test_isdecimal(self):
        assert '0'.isdecimal()
        assert not ''.isdecimal()
        assert not 'a'.isdecimal()
        assert not '\u2460'.isdecimal() # CIRCLED DIGIT ONE

    def test_isnumeric(self):
        assert '0'.isnumeric()
        assert not ''.isnumeric()
        assert not 'a'.isnumeric()
        assert '\u2460'.isnumeric() # CIRCLED DIGIT ONE

    def test_replace_autoconvert(self):
        res = 'one!two!three!'.replace('!', '@', 1)
        assert res == 'one@two!three!'
        assert type(res) == str

    def test_join_subclass(self):
        class StrSubclass(str):
            pass
        class BytesSubclass(bytes):
            pass

        s1 = StrSubclass('a')
        assert ''.join([s1]) is not s1
        s2 = BytesSubclass(b'a')
        assert b''.join([s2]) is not s2

    def test_encoding_and_errors_cant_be_none(self):
        raises(TypeError, "b''.decode(None)")
        raises(TypeError, "u''.encode(None)")
        raises(TypeError, "str(b'', encoding=None)")
        raises(TypeError, 'u"".encode("utf-8", None)')

    def test_casefold(self):
        assert u'hello'.casefold() == u'hello'
        assert u'hELlo'.casefold() == u'hello'
        assert u'ß'.casefold() == u'ss'
        assert u'ﬁ'.casefold() == u'fi'
        assert u'\u03a3'.casefold() == u'\u03c3'
        assert u'A\u0345\u03a3'.casefold() == u'a\u03b9\u03c3'
        assert u'\u00b5'.casefold() == u'\u03bc'

    def test_lower_3a3(self):
        # Special case for GREEK CAPITAL LETTER SIGMA U+03A3
        assert u'\u03a3'.lower() == u'\u03c3'
        assert u'\u0345\u03a3'.lower() == u'\u0345\u03c3'
        assert u'A\u0345\u03a3'.lower() == u'a\u0345\u03c2'
        assert u'A\u0345\u03a3a'.lower() == u'a\u0345\u03c3a'
        assert u'A\u0345\u03a3'.lower() == u'a\u0345\u03c2'
        assert u'A\u03a3\u0345'.lower() == u'a\u03c2\u0345'
        assert u'\u03a3\u0345 '.lower() == u'\u03c3\u0345 '

