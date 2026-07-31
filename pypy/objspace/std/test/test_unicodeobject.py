# -*- encoding: utf-8 -*-
import py, os
try:
    from hypothesis import given, strategies, settings, example
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

from rpython.rlib import rutf8
from pypy.interpreter.error import OperationError
from pypy.objspace.std.unicodeobject import unicodedb

if HAS_HYPOTHESIS:
    @strategies.composite
    def random_split_input(draw):
        def make_spaces():
            spaces = draw(strategies.text(strategies.characters(whitelist_categories=['Zs']), min_size=1))
            # some discrepancies between pypy2 and 3.11 (uni db 14)
            spaces = u"".join(c for c in spaces if unicodedb.isspace(ord(c)))
            if not spaces:
                spaces = u" "
            return spaces

        length = draw(strategies.integers(min_value=0, max_value=20))
        res_list = []
        all_list = []
        for i in range(length):
            all_list.append(make_spaces())
            next_non_space = draw(strategies.text(min_size=1))
            next_non_space = u"".join(c for c in next_non_space if not unicodedb.isspace(ord(c)))
            if next_non_space:
                all_list.append(next_non_space)
                res_list.append(next_non_space)
        if draw(strategies.booleans()):
            all_list.append(make_spaces())
        return u"".join(all_list), res_list


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

    def test_listview_ascii(self):
        w_str = self.space.newutf8('abcd', 4)
        assert self.space.listview_ascii(w_str) == list("abcd")

    def test_new_shortcut(self):
        space = self.space
        w_uni = self.space.newutf8('abcd', 4)
        w_new = space.call_method(
                space.w_unicode, "__new__", space.w_unicode, w_uni)
        assert w_new is w_uni

    def test_fast_iter(self):
        space = self.space
        w_uni = space.newutf8(u"aä".encode("utf-8"), 2)
        old_index_storage = w_uni._index_storage
        w_iter = space.iter(w_uni)
        w_char1 = w_iter.descr_next(space)
        w_char2 = w_iter.descr_next(space)
        py.test.raises(OperationError, w_iter.descr_next, space)
        assert w_uni._index_storage is old_index_storage
        assert space.eq_w(w_char1, w_uni._getitem_result(space, 0))
        assert space.eq_w(w_char2, w_uni._getitem_result(space, 1))


    if HAS_HYPOTHESIS:
        @given(u=strategies.text(),
               start=strategies.integers(min_value=0, max_value=10),
               len1=strategies.integers(min_value=-1, max_value=10))
        def test_hypo_index_find(self, u, start, len1):
            space = self.space
            if start + len1 < 0:
                return   # skip this case
            v = u[start : start + len1]
            w_u = space.wrap(u)
            w_v = space.wrap(v)
            expected = u.find(v, start, start + len1)
            try:
                w_index = space.call_method(w_u, 'index', w_v,
                                            space.newint(start),
                                            space.newint(start + len1))
            except OperationError as e:
                if not e.match(space, space.w_ValueError):
                    raise
                assert expected == -1
            else:
                assert space.int_w(w_index) == expected >= 0

            w_index = space.call_method(w_u, 'find', w_v,
                                        space.newint(start),
                                        space.newint(start + len1))
            assert space.int_w(w_index) == expected

            rexpected = u.rfind(v, start, start + len1)
            try:
                w_index = space.call_method(w_u, 'rindex', w_v,
                                            space.newint(start),
                                            space.newint(start + len1))
            except OperationError as e:
                if not e.match(space, space.w_ValueError):
                    raise
                assert rexpected == -1
            else:
                assert space.int_w(w_index) == rexpected >= 0

            w_index = space.call_method(w_u, 'rfind', w_v,
                                        space.newint(start),
                                        space.newint(start + len1))
            assert space.int_w(w_index) == rexpected

        @given(random_split_input())
        def test_hypo_split(self, inp):
            space = self.space
            input, expected = inp
            w_u = space.newtext(input.encode('utf8'))
            for methname in ('split', 'rsplit'):
                w_l = space.call_method(w_u, methname)
                l_w = space.unpackiterable(w_l)
                assert len(l_w) == len(expected)
                for i, w_elt in enumerate(l_w):
                    assert space.text_w(w_elt) == expected[i].encode('utf8')
            for maxsplit in range(len(expected)):
                w_l = space.call_method(w_u, 'split', space.w_None, space.newint(maxsplit))
                l_w = space.unpackiterable(w_l)
                assert len(l_w) == maxsplit + 1
                for i, w_elt in enumerate(l_w[:-1]):
                    assert space.text_w(w_elt) == expected[i].encode('utf8')
                assert input.encode('utf8').endswith(space.text_w(l_w[-1]))


    def test_getitem_constant_index_jit(self):
        # test it directly, to prevent only seeing bugs in jitted code
        space = self.space
        u = u"äöabc"
        w_u = self.space.wrap(u)
        for i in range(-len(u), len(u)):
            assert w_u._getitem_result_constant_index_jit(space, i)._utf8 == u[i].encode("utf-8")
        with py.test.raises(OperationError):
            w_u._getitem_result_constant_index_jit(space, len(u))
        with py.test.raises(OperationError):
            w_u._getitem_result_constant_index_jit(space, -len(u) - 1)

    def test_getslice_constant_index_jit(self):
        space = self.space
        u = u"äöabcéééß"
        w_u = self.space.wrap(u)
        for start in range(0, 4):
            for end in range(start, len(u)):
                assert w_u._unicode_sliced_constant_index_jit(space, start, end)._utf8 == u[start: end].encode("utf-8")

    def test_lower_upper_ascii(self):
        from pypy.module.unicodedata.interp_ucd import unicodedb
        # check that ascii chars tolower/toupper still behave sensibly in the
        # unicodedb - unlikely to ever change, but well
        for ch in range(128):
            unilower, = unicodedb.tolower_full(ch)
            assert chr(unilower) == chr(ch).lower()
            uniupper, = unicodedb.toupper_full(ch)
            assert chr(uniupper) == chr(ch).upper()

    def test_latin1_ascii_encode_shortcut_ascii(self, monkeypatch):
        from rpython.rlib import rutf8
        from pypy.objspace.std.unicodeobject import encode_object
        monkeypatch.setattr(rutf8, "check_ascii", None)
        w_b = encode_object(self.space, self.space.newutf8("abc", 3), "latin-1", "strict")
        assert self.space.bytes_w(w_b) == "abc"
        w_b = encode_object(self.space, self.space.newutf8("abc", 3), "ascii", "strict")
        assert self.space.bytes_w(w_b) == "abc"

    def test_utf8_ascii_encode_shortcut_ascii(self, monkeypatch):
        from rpython.rlib import rutf8
        from pypy.objspace.std.unicodeobject import encode_object
        monkeypatch.setattr(rutf8, "check_utf8", None)
        for enc in ["utf-8", "UTF-8", "utf8"]:
            w_b = encode_object(self.space, self.space.newutf8("abc", 3), enc, "strict")
            assert self.space.bytes_w(w_b) == "abc"

    def test_split_shortcut_ascii(self, monkeypatch):
        from rpython.rlib import rutf8
        monkeypatch.setattr(rutf8, "isspace", None)
        w_s = self.space.newutf8("a b c", 5)
        w_l = w_s.descr_split(self.space) # no crash
        assert self.space.len_w(w_l) == 3


class AppTestUnicodeStringStdOnly:
    def test_compares(self):
        assert type('a') != type(b'a')
        assert 'a' != b'a'
        assert b'a' != 'a'
        assert not ('a' == 5)
        assert 'a' != 5
        raises(TypeError, "'a' < 5")
        raises(TypeError, "'a' < bytearray(b'a')")


class AppTestUnicodeString:
    spaceconfig = dict(usemodules=('unicodedata',))

    with open(os.path.join(os.path.dirname(__file__), 'startswith.py')) as f:
        exec 'def test_startswith_endswith_external(self): """%s"""\n' % (
        f.read(),)

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

    @py.test.mark.skipif("not config.option.runappdirect and sys.maxunicode == 0xffff")
    def test_isprintable_wide(self):
        assert '\U0001F46F'.isprintable()  # Since unicode 6.0
        assert not '\U000E0020'.isprintable()
        assert u'\ud800'.capitalize() == u'\ud800'
        assert u'xx\ud800'.capitalize() == u'Xx\ud800'


    def test_partition(self):
        assert (u'this is the par', u'ti', u'tion method') == \
            u'this is the partition method'.partition(u'ti')

        # from raymond's original specification
        S = u'http://www.python.org'
        assert (u'http', u'://', u'www.python.org') == S.partition(u'://')
        assert (u'http://www.python.org', u'', u'') == S.partition(u'?')
        assert (u'', u'http://', u'www.python.org') == S.partition(u'http://')
        assert (u'http://www.python.', u'org', u'') == S.partition(u'org')

        raises(ValueError, S.partition, u'')
        raises(TypeError, S.partition, None)

    def test_rpartition(self):
        assert (u'this is the rparti', u'ti', u'on method') == \
            u'this is the rpartition method'.rpartition(u'ti')

        # from raymond's original specification
        S = u'http://www.python.org'
        assert (u'http', u'://', u'www.python.org') == S.rpartition(u'://')
        assert (u'', u'', u'http://www.python.org') == S.rpartition(u'?')
        assert (u'', u'http://', u'www.python.org') == S.rpartition(u'http://')
        assert (u'http://www.python.', u'org', u'') == S.rpartition(u'org')

        raises(ValueError, S.rpartition, u'')
        raises(TypeError, S.rpartition, None)

    def test_partition_str_unicode(self):
        x = 'abbbd'.rpartition(u'bb')
        assert x == (u'ab', u'bb', u'd')
        assert map(type, x) == [unicode, unicode, unicode]
        raises(UnicodeDecodeError, '\x80'.partition, u'')
        raises(UnicodeDecodeError, '\x80'.rpartition, u'')

    def test_mul(self):
        zero = 0
        assert type(u'' * zero) == type(zero * u'') == unicode
        assert u'' * zero == zero * u'' == u''
        assert u'x' * zero == zero * u'x' == u''
        assert type(u'x' * zero) == type(zero * u'x') == unicode
        assert u'123' * zero == zero * u'123' == u''
        assert type(u'123' * zero) == type(zero * u'123') == unicode
        for i in range(10):
            u = u'123' * i
            assert len(u) == 3*i
            for j in range(0, i, 3):
                assert u[j+0] == u'1'
                assert u[j+1] == u'2'
                assert u[j+2] == u'3'
            assert u'123' * i == i * u'123'

    def test_index(self):
        assert u"rrarrrrrrrrra".index(u'a', 4, None) == 12
        assert u"rrarrrrrrrrra".index(u'a', None, 6) == 2
        assert u"\u1234\u4321\u5678".index(u'\u5678', 1) == 2

    def test_rindex(self):
        from sys import maxint
        assert u'abcdefghiabc'.rindex(u'') == 12
        assert u'abcdefghiabc'.rindex(u'def') == 3
        assert u'abcdefghiabc'.rindex(u'abc') == 9
        assert u'abcdefghiabc'.rindex(u'abc', 0, -1) == 0
        assert u'abcdefghiabc'.rindex(u'abc', -4*maxint, 4*maxint) == 9
        assert u'rrarrrrrrrrra'.rindex(u'a', 4, None) == 12
        assert u"\u1234\u5678".rindex(u'\u5678') == 1

        raises(ValueError, u'abcdefghiabc'.rindex, u'hib')
        raises(ValueError, u'defghiabc'.rindex, u'def', 1)
        raises(ValueError, u'defghiabc'.rindex, u'abc', 0, -1)
        raises(ValueError, u'abcdefghi'.rindex, u'ghi', 0, 8)
        raises(ValueError, u'abcdefghi'.rindex, u'ghi', 0, -1)
        raises(TypeError, u'abcdefghijklmn'.rindex, u'abc', 0, 0.0)
        raises(TypeError, u'abcdefghijklmn'.rindex, u'abc', -10.0, 30)

    def test_rfind(self):
        assert u'abcdefghiabc'.rfind(u'abc') == 9
        assert u'abcdefghiabc'.rfind(u'') == 12
        assert u'abcdefghiabc'.rfind(u'abcd') == 0
        assert u'abcdefghiabc'.rfind(u'abcz') == -1
        assert u"\u1234\u5678".rfind(u'\u5678') == 1

    def test_rfind_corner_case(self):
        assert u'abc'.rfind('', 4) == -1

    def test_find_index_str_unicode(self):
        assert u'abcdefghiabc'.find(u'bc') == 1
        assert u'ab\u0105b\u0107'.find('b', 2) == 3
        assert u'ab\u0105b\u0107'.find('b', 0, 1) == -1
        assert 'abcdefghiabc'.rfind(u'abc') == 9
        raises(UnicodeDecodeError, '\x80'.find, u'')
        raises(UnicodeDecodeError, '\x80'.rfind, u'')
        assert 'abcdefghiabc'.index(u'bc') == 1
        assert 'abcdefghiabc'.rindex(u'abc') == 9
        raises(UnicodeDecodeError, '\x80'.index, u'')
        raises(UnicodeDecodeError, '\x80'.rindex, u'')
        assert u"\u1234\u5678".find(u'\u5678') == 1

    def test_count_unicode(self):
        assert u'aaa'.count('', 10) == 0
        assert u'aaa'.count('', 3) == 1
        assert u"".count(u"x") ==0
        assert u"".count(u"") ==1
        assert u"Python".count(u"") ==7
        assert u"ab aaba".count(u"ab") ==2
        assert u'aaa'.count(u'a') == 3
        assert u'aaa'.count(u'b') == 0
        assert u'aaa'.count(u'a', -1) == 1
        assert u'aaa'.count(u'a', -10) == 3
        assert u'aaa'.count(u'a', 0, -1) == 2
        assert u'aaa'.count(u'a', 0, -10) == 0
        assert u'ababa'.count(u'aba') == 1

        # An empty string matches between code points, so the result must not
        # depend on the number of bytes used to encode the receiver.
        assert u'\xe9\xe8\xe9\xe8\xe9'.count(u'') == 6
        assert u'\u4e00\u4e8c'.count(u'') == 3
        assert u'\U0001f600'.count(u'') == 2
        assert u'a\xe9\u4e00\U0001f600'.count(u'') == 5
        assert u'\xe9\xe8\xe9\xe8\xe9'.count(u'', 1, 3) == 3
        for s in [u'aaa', u'\xe9\xe8\xe9', u'\u4e00\u4e8c',
                  u'\U0001f600', u'a\xe9\u4e00\U0001f600']:
            assert s.count(u'') == len(s) + 1
            assert s.count(u'') == s.rfind(u'') - s.find(u'') + 1

    def test_count_str_unicode(self):
        assert 'aaa'.count(u'a') == 3
        assert 'aaa'.count(u'b') == 0
        assert 'aaa'.count(u'a', -1) == 1
        assert 'aaa'.count(u'a', -10) == 3
        assert 'aaa'.count(u'a', 0, -1) == 2
        assert 'aaa'.count(u'a', 0, -10) == 0
        assert 'ababa'.count(u'aba') == 1
        raises(UnicodeDecodeError, '\x80'.count, u'')

    def test_swapcase(self):
        assert u'\xe4\xc4\xdf'.swapcase() == u'\xc4\xe4\xdf'
        assert u'\ud800'.swapcase() == u'\ud800'

    def test_buffer(self):
        buf = buffer(u'XY')
        assert str(buf) in ['X\x00Y\x00',
                            '\x00X\x00Y',
                            'X\x00\x00\x00Y\x00\x00\x00',
                            '\x00\x00\x00X\x00\x00\x00Y']

    def test_call_special_methods(self):
        # xxx not completely clear if these are implementation details or not
        assert 'abc'.__add__(u'def') == u'abcdef'
        assert u'abc'.__add__(u'def') == u'abcdef'
        assert u'abc'.__add__('def') == u'abcdef'
        assert u'abc'.__rmod__(u'%s') == u'abc'
        ret = u'abc'.__rmod__('%s')
        raises(AttributeError, "u'abc'.__radd__(u'def')")

    def test_str_unicode_concat_overrides(self):
        "Test from Jython about being bug-compatible with CPython."

        def check(value, expected):
            assert type(value) == type(expected)
            assert value == expected

        def _test_concat(t1, t2):
            tprecedent = str
            if issubclass(t1, unicode) or issubclass(t2, unicode):
                tprecedent = unicode

            class SubclassB(t2):
                def __add__(self, other):
                    return SubclassB(t2(self) + t2(other))
            check(SubclassB('py') + SubclassB('thon'), SubclassB('python'))
            check(t1('python') + SubclassB('3'), tprecedent('python3'))
            check(SubclassB('py') + t1('py'), SubclassB('pypy'))

            class SubclassC(t2):
                def __radd__(self, other):
                    return SubclassC(t2(other) + t2(self))
            check(SubclassC('stack') + SubclassC('less'), t2('stackless'))
            check(t1('iron') + SubclassC('python'), SubclassC('ironpython'))
            check(SubclassC('tiny') + t1('py'), tprecedent('tinypy'))

            class SubclassD(t2):
                def __add__(self, other):
                    return SubclassD(t2(self) + t2(other))

                def __radd__(self, other):
                    return SubclassD(t2(other) + t2(self))
            check(SubclassD('di') + SubclassD('ct'), SubclassD('dict'))
            check(t1('list') + SubclassD(' comp'), SubclassD('list comp'))
            check(SubclassD('dun') + t1('der'), SubclassD('dunder'))

        _test_concat(str, str)
        _test_concat(unicode, unicode)
        # the following two cases are really there to emulate a CPython bug.
        _test_concat(str, unicode)   # uses hack in add__String_Unicode()
        _test_concat(unicode, str)   # uses hack in descroperation.binop_impl()

    def test_returns_subclass(self):
        class X(unicode):
            pass

        class Y(object):
            def __unicode__(self):
                return X("stuff")

        assert unicode(Y()).__class__ is X

    def test_getslice(self):
        assert u'123456'.__getslice__(1, 5) == u'2345'
        s = u"\u0105b\u0107"
        assert s[:] == u"\u0105b\u0107"
        assert s[1:] == u"b\u0107"
        assert s[:2] == u"\u0105b"
        assert s[1:2] == u"b"
        assert s[-2:] == u"b\u0107"
        assert s[:-1] == u"\u0105b"
        assert s[-2:2] == u"b"
        assert s[1:-1] == u"b"
        assert s[-2:-1] == u"b"

    def test_getitem_slice(self):
        assert u'123456'.__getitem__(slice(1, 5)) == u'2345'
        s = u"\u0105b\u0107"
        assert s[slice(3)] == u"\u0105b\u0107"
        assert s[slice(1, 3)] == u"b\u0107"
        assert s[slice(2)] == u"\u0105b"
        assert s[slice(1,2)] == u"b"
        assert s[slice(-2,3)] == u"b\u0107"
        assert s[slice(-1)] == u"\u0105b"
        assert s[slice(-2,2)] == u"b"
        assert s[slice(1,-1)] == u"b"
        assert s[slice(-2,-1)] == u"b"
        assert u"abcde"[::2] == u"ace"
        assert u"\u0105\u0106\u0107abcd"[::2] == u"\u0105\u0107bd"

    def test_no_len_on_str_iter(self):
        iterable = u"hello"
        raises(TypeError, len, iter(iterable))

    def test_encode_raw_unicode_escape(self):
        u = unicode('\\', 'raw_unicode_escape')
        assert u == u'\\'

    def test_decode_from_buffer(self):
        buf = buffer('character buffers are decoded to unicode')
        u = unicode(buf, 'utf-8', 'strict')
        assert u == u'character buffers are decoded to unicode'

    def test_unicode_conversion_with__unicode__(self):
        class A(unicode):
            def __unicode__(self):
                return "foo"
        class B(unicode):
            pass
        a = A('bar')
        assert a == 'bar'
        assert unicode(a) == 'foo'
        b = B('bar')
        assert b == 'bar'
        assert unicode(b) == 'bar'

    def test_unicode_conversion_with__str__(self):
        # new-style classes
        class A(object):
            def __str__(self):
                return u'\u1234'
        s = unicode(A())
        assert type(s) is unicode
        assert s == u'\u1234'
        # with old-style classes, it's different, but it should work as well
        class A:
            def __str__(self):
                return u'\u1234'
        s = unicode(A())
        assert type(s) is unicode
        assert s == u'\u1234'

    def test_formatting_unicode__str__(self):
        class A:
            def __init__(self, num):
                self.num = num
            def __str__(self):
                return unichr(self.num)

        s = '%s' % A(111)    # this is ASCII
        assert type(s) is unicode
        assert s == chr(111)

        s = '%s' % A(0x1234)    # this is not ASCII
        assert type(s) is unicode
        assert s == u'\u1234'

        # now the same with a new-style class...
        class A(object):
            def __init__(self, num):
                self.num = num
            def __str__(self):
                return unichr(self.num)

        s = '%s' % A(111)    # this is ASCII
        assert type(s) is unicode
        assert s == chr(111)

        s = '%s' % A(0x1234)    # this is not ASCII
        assert type(s) is unicode
        assert s == u'\u1234'

    def test_formatting_unicode__str__2(self):
        class A:
            def __str__(self):
                return u'baz'

        class B:
            def __str__(self):
                return 'foo'

            def __unicode__(self):
                return u'bar'

        a = A()
        b = B()
        s = '%s %s' % (a, b)
        assert s == u'baz bar'

        skip("but this case here is completely insane")
        s = '%s %s' % (b, a)
        assert s == u'foo baz'

    def test_formatting_unicode__str__3(self):
        # "bah" is all I can say
        class X(object):
            def __repr__(self):
                return u'\u1234'
        '%s' % X()
        #
        class X(object):
            def __str__(self):
                return u'\u1234'
        '%s' % X()

    def test_format_repeat(self):
        assert format(u"abc", u"z<5") == u"abczz"
        assert format(u"abc", u"\u2007<5") == u"abc\u2007\u2007"
        # raises UnicodeEncodeError, like CPython does
        raises(UnicodeEncodeError, format, 123, u"\u2007<5")

    def test_formatting_char(self):
        for num in range(0x80,0x100):
            uchar = unichr(num)
            print num
            assert uchar == u"%c" % num   # works only with ints
            assert uchar == u"%c" % uchar # and unicode chars
            # the implicit decoding should fail for non-ascii chars
            raises(UnicodeDecodeError, u"%c".__mod__, chr(num))
            raises(UnicodeDecodeError, u"%s".__mod__, chr(num))

    def test_str_subclass(self):
        class Foo9(str):
            def __unicode__(self):
                return u"world"
        assert unicode(Foo9("hello")) == u"world"

    def test_class_with_both_str_and_unicode(self):
        class A(object):
            def __str__(self):
                return 'foo'

            def __unicode__(self):
                return u'bar'

        assert unicode(A()) == u'bar'

        class A:
            def __str__(self):
                return 'foo'

            def __unicode__(self):
                return u'bar'

        assert unicode(A()) == u'bar'

    def test_format_unicode_subclass(self):
        class U(unicode):
            def __unicode__(self):
                return u'__unicode__ overridden'
        u = U(u'xxx')
        assert repr("%s" % u) == "u'__unicode__ overridden'"
        assert repr("{}".format(u)) == "'__unicode__ overridden'"

    def test_format_c_overflow(self):
        import sys
        raises(OverflowError, u'{0:c}'.format, -1)
        raises(OverflowError, u'{0:c}'.format, sys.maxunicode + 1)

    def test_replace_with_buffer(self):
        assert u'abc'.replace(buffer('b'), buffer('e')) == u'aec'
        assert u'abc'.replace(buffer('b'), u'e') == u'aec'
        assert u'abc'.replace(u'b', buffer('e')) == u'aec'

    def test_unicode_subclass(self):
        class S(unicode):
            pass

        a = S(u'hello \u1234')
        b = unicode(a)
        assert type(b) is unicode
        assert b == u'hello \u1234'

        assert u'%s' % S(u'mar\xe7') == u'mar\xe7'

    def test_isdecimal(self):
        assert u'0'.isdecimal()
        assert not u''.isdecimal()
        assert not u'a'.isdecimal()
        assert not u'\u2460'.isdecimal() # CIRCLED DIGIT ONE

    def test_isnumeric(self):
        assert u'0'.isnumeric()
        assert not u''.isnumeric()
        assert not u'a'.isnumeric()
        assert u'\u2460'.isnumeric() # CIRCLED DIGIT ONE

    def test_replace_str_unicode(self):
        res = 'one!two!three!'.replace(u'!', u'@', 1)
        assert res == u'one@two!three!'
        assert type(res) == unicode
        raises(UnicodeDecodeError, '\x80'.replace, 'a', u'b')
        raises(UnicodeDecodeError, '\x80'.replace, u'a', 'b')

    def test_join_subclass(self):
        class UnicodeSubclass(unicode):
            pass
        class StrSubclass(str):
            pass

        s1 = UnicodeSubclass(u'a')
        assert u''.join([s1]) is not s1
        s2 = StrSubclass(u'a')
        assert u''.join([s2]) is not s2

    def test_encoding_and_errors_cant_be_none(self):
        raises(TypeError, "''.decode(None)")
        raises(TypeError, "u''.encode(None)")
        raises(TypeError, "unicode('', encoding=None)")
        raises(TypeError, 'u"".encode("utf-8", None)')

    def test_unicode_constructor_misc(self):
        x = u'foo'
        x += u'bar'
        assert unicode(x) is x
        #
        class U(unicode):
            def __unicode__(self):
                return u'BOK'
        u = U(x)
        assert unicode(u) == u'BOK'
        #
        class U2(unicode):
            pass
        z = U2(u'foobaz')
        assert type(unicode(z)) is unicode
        assert unicode(z) == u'foobaz'
        #
        assert unicode(encoding='supposedly_the_encoding') == u''
        assert unicode(errors='supposedly_the_error') == u''
        e = raises(TypeError, unicode, u'', 'supposedly_the_encoding')
        assert str(e.value) == 'decoding Unicode is not supported'
        e = raises(TypeError, unicode, u'', errors='supposedly_the_error')
        assert str(e.value) == 'decoding Unicode is not supported'
        e = raises(TypeError, unicode, u, 'supposedly_the_encoding')
        assert str(e.value) == 'decoding Unicode is not supported'
        e = raises(TypeError, unicode, z, 'supposedly_the_encoding')
        assert str(e.value) == 'decoding Unicode is not supported'

    def test_newlist_utf8_non_ascii(self):
        'ä'.split("\n")[0] # does not crash

    def test_replace_no_occurrence(self):
        x = u"xyz"
        assert x.replace(u"a", u"b") is x
