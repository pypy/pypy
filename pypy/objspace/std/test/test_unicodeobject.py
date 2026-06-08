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


