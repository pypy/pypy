"""Test unicode/str's format method"""
from __future__ import with_statement
from pypy.conftest import gettestobjspace


class BaseStringFormatTests:
    """Test format and __format__ methods of string objects."""

    def test_escape(self):
        assert self.s("{{").format() == "{"
        assert self.s("}}").format() == "}"
        assert self.s("{} {{ {}").format(1, 2) == "1 { 2"
        assert self.s("{{}}").format() == "{}"
        assert self.s("{{{{").format() == "{{"

    def test_empty(self):
        assert self.s().format() == ""
        assert self.s("x").format() == "x"

    def test_several(self):
        assert self.s("x{} stuff {}m").format(32, 42) == "x32 stuff 42m"

    def test_stray_brackets(self):
        raises(ValueError, self.s("}").format, 3)
        raises(ValueError, self.s("{").format, 3)
        raises(ValueError, self.s("{}}").format, 3)

    def test_auto_numbering(self):
        assert self.s("{} {name} {}").format(1, 2, name=3) == "1 3 2"
        raises(ValueError, self.s("{} {2}").format, 2, 3)
        raises(ValueError, self.s("{0} {}").format, 2, 3)

    def test_positional_args(self):
        assert self.s("{1}{0}").format(2, 3) == "32"
        raises(IndexError, self.s("{2}").format, 2)
        big = self.s("{123476028570192873049182730984172039840712934}")
        raises(ValueError, big.format)

    def test_kwargs(self):
        assert self.s("{what}").format(what=42) == "42"
        raises(KeyError, self.s("{nothing}").format)

    def test_attr(self):
        class x:
            apple = 42
        assert self.s("{.apple}").format(x) == "42"
        #
        raises(ValueError, self.s("{.}").format, x)

    def test_index(self):
        seq = (1, 42)
        assert self.s("{[1]}").format(seq) == "42"
        big = self.s("{[1092837041982035981720398471029384012937412]}")
        raises(ValueError, big.format, [0])

    def test_getitem(self):
        d = {"hi" : 32}
        assert self.s("{[hi]}").format(d) == "32"

    def test_chained(self):
        class x:
            y = [1, 2, 3]
        assert self.s("{.y[1]}").format(x) == "2"
        l = [1, x]
        assert self.s("{[1].y[2]}").format(l) == "3"

    def test_invalid_field_name(self):
        raises(ValueError, self.s("{[x]y}").format, {"x" : 2})

    def test_repr_conversion(self):
        class x(object):
            def __repr__(self):
                return "32"
        assert self.s("{!r}").format(x()) == "32"
        assert self.s("{!s}").format(x()) == "32"

    def test_format_spec(self):
        assert self.s('{0!s:}').format('Hello') == 'Hello'
        assert self.s('{0!s:15}').format('Hello') == 'Hello          '
        assert self.s('{0!s:15s}').format('Hello') == 'Hello          '
        assert self.s('{0!r}').format('Hello') == "'Hello'"
        assert self.s('{0!r:}').format('Hello') == "'Hello'"

    def test_invalid_conversion(self):
        raises(ValueError, self.s("{!x}").format, 3)
        raises(ValueError, self.s("{!}").format)

    def test_recursive(self):
        assert self.s("{:{}}").format(42, "#o") == "0o52"
        raises(ValueError, self.s("{{}:s}").format)
        raises(ValueError, self.s("{:{:{}}}").format, 1, 2, 3)

    def test_presentation(self):
        assert format(self.s("blah"), "s") == "blah"
        assert format(self.s("blah")) == "blah"
        for pres in "bcdoxXeEfFgGn%":
            raises(ValueError, format, self.s("blah"), pres)

    def test_padding(self):
        assert format(self.s("h"), "3") == "h  "
        assert format(self.s("h"), "<3") == "h  "
        assert format(self.s("h"), ">3") == "  h"
        assert format(self.s("h"), "^3") == " h "
        assert format(self.s("h"), "^4") == " h  "
        assert format(self.s("h"), "c<3") == "hcc"
        raises(ValueError, format, self.s("blah"), "=12")

    def test_precision(self):
        assert format(self.s("abcdef"), ".3") == "abc"

    def test_non_ascii_presentation(self):
        raises(ValueError, format, self.s(""), "\x234")

    def test_oldstyle_custom_format(self):
        import warnings

        class C:
            def __init__(self, x=100):
                self._x = x
            def __format__(self, spec):
                return spec
        class D:
            def __init__(self, x):
                self.x = x
            def __format__(self, spec):
                return str(self.x)
        class E:
            def __init__(self, x):
                self.x = x
            def __str__(self):
                return 'E(' + self.x + ')'
        class G:
            def __init__(self, x):
                self.x = x
            def __str__(self):
                return "string is " + self.x
            def __format__(self, format_spec):
                if format_spec == 'd':
                    return 'G(' + self.x + ')'
                return object.__format__(self, format_spec)

        assert self.s("{1}{0}").format(D(10), D(20)) == "2010"
        assert self.s("{0._x.x}").format(C(D("abc"))) == "abc"
        assert self.s("{0[1][0].x}").format(["abc", [D("def")]]) == "def"
        assert self.s("{0}").format(E("data")) == "E(data)"
        assert self.s("{0:d}").format(G("data")) == "G(data)"
        assert self.s("{0!s}").format(G("data")) == "string is data"

        msg = "object.__format__ with a non-empty format string is deprecated",
        with warnings.catch_warnings(record=True) as log:
            # This is ok because warnings.catch_warnings resets the filters
            warnings.simplefilter("always", PendingDeprecationWarning)
            assert self.s("{0:^10}").format(E("data")) == " E(data)  "
            assert log[0].message.args == msg
            assert type(log[0].message) is PendingDeprecationWarning

            assert self.s("{0:^10s}").format(E("data")) == " E(data)  "
            assert log[1].message.args == msg
            assert type(log[1].message) is PendingDeprecationWarning

            assert self.s("{0:>15s}").format(G("data")) == " string is data"
            assert log[2].message.args == msg
            assert type(log[2].message) is PendingDeprecationWarning
        assert len(log) == 3

    def test_bogus_cases(self):
        raises(KeyError, '{0]}'.format, 5)
        raises(ValueError, '{0!r'.format, 5)
        raises(ValueError, '{0!rs}'.format, 5)


class AppTestUnicodeFormat(BaseStringFormatTests):

    def setup_class(cls):
        cls.w_s = cls.space.w_unicode

    def test_string_conversion(self):
        class x(object):
            def __repr__(self):
                return "32"
            def __str__(self):
                return "18"
        assert self.s("{!s}").format(x()) == "18"
        assert self.s("{!r}").format(x()) == "32"

    def test_non_latin1_key(self):
        raises(KeyError, self.s("{\u1000}").format)



class BaseIntegralFormattingTest:

    def test_simple(self):
        assert format(self.i(2)) == "2"
        assert isinstance(format(self.i(2), ""), str)

    def test_invalid(self):
        raises(ValueError, format, self.i(8), "s")
        raises(ValueError, format, self.i(8), ".3")

    def test_c(self):
        a = self.i(ord("a"))
        assert format(a, "c") == "a"
        raises(ValueError, format, a, "-c")
        raises(ValueError, format, a, ",c")
        assert format(a, "3c") == "  a"
        assert format(a, "<3c") == "a  "
        assert format(a, "^3c") == " a "
        assert format(a, "=3c") == "  a"
        assert format(a, "x^3c") == "xax"

    def test_binary(self):
        assert format(self.i(2), "b") == "10"
        assert format(self.i(2), "#b") == "0b10"

    def test_octal(self):
        assert format(self.i(8), "o") == "10"
        assert format(self.i(8), "#o") == "0o10"
        assert format(self.i(-8), "o") == "-10"
        assert format(self.i(-8), "#o") == "-0o10"
        assert format(self.i(8), "+o") == "+10"
        assert format(self.i(8), "+#o") == "+0o10"

    def test_hex(self):
        assert format(self.i(16), "x") == "10"
        assert format(self.i(16), "#x") == "0x10"
        assert format(self.i(10), "x") == "a"
        assert format(self.i(10), "#x") == "0xa"
        assert format(self.i(10), "X") == "A"
        assert format(self.i(10), "#X") == "0XA"

    def test_padding(self):
        assert format(self.i(6), "3") == "  6"
        assert format(self.i(6), ">3") == "  6"
        assert format(self.i(6), "<3") == "6  "
        assert format(self.i(6), "=3") == "  6"
        assert format(self.i(6), "=+3") == "+ 6"
        assert format(self.i(6), "a^3") == "a6a"
        assert format(self.i(6), "03") == "006"

    def test_width_overflow(self):
        big = "92387405982730948052983740958230948524"
        raises(ValueError, format, self.i(2), big)

    def test_sign(self):
        assert format(self.i(-6)) == "-6"
        assert format(self.i(-6), "-") == "-6"
        assert format(self.i(-6), "+") == "-6"
        assert format(self.i(-6), " ") == "-6"
        assert format(self.i(6), " ") == " 6"
        assert format(self.i(6), "-") == "6"
        assert format(self.i(6), "+") == "+6"

    def test_thousands_separator(self):
        assert format(self.i(123), ",") == "123"
        assert format(self.i(12345), ",") == "12,345"
        assert format(self.i(123456789), ",") == "123,456,789"
        assert format(self.i(12345), "7,") == " 12,345"
        assert format(self.i(12345), "<7,") == "12,345 "
        assert format(self.i(1234), "0=10,") == "00,001,234"
        assert format(self.i(1234), "010,") == "00,001,234"


class AppTestIntFormatting(BaseIntegralFormattingTest):

    def setup_class(cls):
        cls.w_i = cls.space.w_int


class AppTestFloatFormatting:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_locale',))

    def test_alternate(self):
        raises(ValueError, format, 1.0, "#")

    def test_simple(self):
        assert format(0.0, "f") == "0.000000"

    def test_sign(self):
        assert format(-1.23, "1") == "-1.23"
        x = 100.0 / 7.0
        s = str(x)
        assert format(x) == s
        assert format(x, "-") == s
        assert format(x, " ") == ' ' + s
        assert format(x, "+") == '+' + s
        assert format(-x, "-") == '-' + s
        assert format(-x, " ") == '-' + s
        assert format(-x, "+") == '-' + s

    def test_digit_separator(self):
        assert format(-1234., "012,f") == "-1,234.000000"

    def test_locale(self):
        import locale
        for name in ['en_US.UTF8', 'en_US', 'en']:
            try:
                locale.setlocale(locale.LC_NUMERIC, name)
                break
            except locale.Error:
                pass
        else:
            skip("no 'en' or 'en_US' or 'en_US.UTF8' locale??")
        x = 1234.567890
        try:
            assert locale.format('%g', x, grouping=True) == '1,234.57'
            assert format(x, 'n') == '1,234.57'
        finally:
            locale.setlocale(locale.LC_NUMERIC, 'C')

    def test_dont_switch_to_g(self):
        skip("must fix when float formatting is figured out")
        assert len(format(1.1234e90, "f")) == 98

    def test_infinite(self):
        inf = 1e400
        nan = inf/inf
        assert format(inf, "f") == "inf"
        assert format(inf, "F") == "INF"
        assert format(nan, "f") == "nan"
        assert format(nan, "F") == "NAN"


class AppTestInternalMethods:
    # undocumented API on string and unicode object, but used by string.py

    def test_formatter_parser(self):
        import _string
        l = list(_string.formatter_parser('abcd'))
        assert l == [('abcd', None, None, None)]
        #
        l = list(_string.formatter_parser('ab{0}cd'))
        assert l == [('ab', '0', '', None), ('cd', None, None, None)]
        #
        l = list(_string.formatter_parser('{0}cd'))
        assert l == [('', '0', '', None), ('cd', None, None, None)]
        #
        l = list(_string.formatter_parser('ab{0}'))
        assert l == [('ab', '0', '', None)]
        #
        l = list(_string.formatter_parser(''))
        assert l == []
        #
        l = list(_string.formatter_parser('{0:123}'))
        assert l == [('', '0', '123', None)]
        #
        l = list(_string.formatter_parser('{0!x:123}'))
        assert l == [('', '0', '123', 'x')]
        #
        l = list(_string.formatter_parser('{0!x:12{sdd}3}'))
        assert l == [('', '0', '12{sdd}3', 'x')]

    def test_u_formatter_parser(self):
        import _string
        l = list(_string.formatter_parser('{0!x:12{sdd}3}'))
        assert l == [('', '0', '12{sdd}3', 'x')]
        for x in l[0]:
            assert isinstance(x, str)

    def test_formatter_parser_escape(self):
        l = list("{{a}}"._formatter_parser())
        assert l == [('{', None, None, None), ('a}', None, None, None)]
        l = list("{{{{"._formatter_parser())
        assert l == [('{', None, None, None), ('{', None, None, None)]

    def test_formatter_field_name_split(self):
        import _string
        first, rest = _string.formatter_field_name_split('')
        assert first == ''
        assert list(rest) == []
        #
        first, rest = _string.formatter_field_name_split('31')
        assert first == 31
        assert list(rest) == []
        #
        first, rest = _string.formatter_field_name_split('foo')
        assert first == 'foo'
        assert list(rest) == []
        #
        first, rest = _string.formatter_field_name_split('foo.bar')
        assert first == 'foo'
        assert list(rest) == [(True, 'bar')]
        #
        first, rest = _string.formatter_field_name_split('foo[123]')
        assert first == 'foo'
        assert list(rest) == [(False, 123)]
        #
        first, rest = _string.formatter_field_name_split('foo.baz[123].bok')
        assert first == 'foo'
        assert list(rest) == [(True, 'baz'), (False, 123), (True, 'bok')]
        #
        first, rest = _string.formatter_field_name_split('foo.baz[hi].bok')
        assert first == 'foo'
        assert list(rest) == [(True, 'baz'), (False, 'hi'), (True, 'bok')]

    def test_u_formatter_field_name_split(self):
        import _string
        first, rest = _string.formatter_field_name_split('foo.baz[hi].bok')
        l = list(rest)
        assert first == 'foo'
        assert l == [(True, 'baz'), (False, 'hi'), (True, 'bok')]
        assert isinstance(first, str)
        for x, y in l:
            assert isinstance(y, str)
