"""Test unicode/str's format method"""


class BaseStringFormatTests:
    """Test format and __format__ methods of string objects."""

    def test_escape(self):
        assert self.s("{{").format() == self.s("{")
        assert self.s("}}").format() == self.s("}")
        assert self.s("{} {{ {}").format(1, 2) == self.s("1 { 2")
        assert self.s("{{}}").format() == self.s("{}")

    def test_empty(self):
        assert self.s().format() == self.s()
        assert self.s("x").format() == self.s("x")

    def test_several(self):
        res = self.s("x32 stuff 42m")
        assert self.s("x{} stuff {}m").format(32, 42) == res

    def test_stray_brackets(self):
        raises(ValueError, self.s("}").format, 3)
        raises(ValueError, self.s("{").format, 3)
        raises(ValueError, self.s("{}}").format, 3)

    def test_auto_numbering(self):
        res = "1 3 2"
        assert self.s("{} {name} {}").format(1, 2, name=3) == self.s(res)
        raises(ValueError, self.s("{} {2}").format, 2, 3)
        raises(ValueError, self.s("{0} {}").format, 2, 3)

    def test_positional_args(self):
        assert self.s("{1}{0}").format(2, 3) == self.s("32")
        raises(IndexError, self.s("{2}").format, 2)
        big = self.s("{123476028570192873049182730984172039840712934}")
        raises(ValueError, big.format)

    def test_kwargs(self):
        assert self.s("{what}").format(what=42) == self.s("42")
        raises(KeyError, self.s("{nothing}").format)

    def test_attr(self):
        class x:
            apple = 42
        assert self.s("{.apple}").format(x) == self.s("42")

    def test_index(self):
        seq = (1, 42)
        assert self.s("{[1]}").format(seq) == self.s("42")
        big = self.s("{[1092837041982035981720398471029384012937412]}")
        raises(ValueError, big.format, [0])

    def test_getitem(self):
        d = {"hi" : 32}
        assert self.s("{[hi]}").format(d) == self.s("32")

    def test_chained(self):
        class x:
            y = [1, 2, 3]
        assert self.s("{.y[1]}").format(x) == self.s("2")
        l = [1, x]
        assert self.s("{[1].y[2]}").format(l) == self.s("3")

    def test_invalid_field_name(self):
        raises(ValueError, self.s("{[x]y}").format, {"x" : 2})

    def test_repr_conversion(self):
        class x(object):
            def __repr__(self):
                return "32"
        assert self.s("{!r}").format(x()) == self.s("32")
        assert self.s("{!s}").format(x()) == self.s("32")

    def test_invalid_conversion(self):
        raises(ValueError, self.s("{!x}").format, 3)
        raises(ValueError, self.s("{!}").format)

    def test_recursive(self):
        assert self.s("{:{}}").format(42, "#o") == self.s("0o52")
        raises(ValueError, self.s("{{}:s}").format)
        raises(ValueError, self.s("{:{:{}}}").format, 1, 2, 3)

    def test_presentation(self):
        assert format(self.s("blah"), "s") == self.s("blah")
        assert format(self.s("blah")) == self.s("blah")
        for pres in "bcdoxXeEfFgGn%":
            raises(ValueError, format, self.s("blah"), pres)

    def test_padding(self):
        assert format(self.s("h"), "3") == self.s("h  ")
        assert format(self.s("h"), "<3") == self.s("h  ")
        assert format(self.s("h"), ">3") == self.s("  h")
        assert format(self.s("h"), "^3") == self.s(" h ")
        assert format(self.s("h"), "^4") == self.s(" h  ")
        assert format(self.s("h"), "c<3") == self.s("hcc")
        raises(ValueError, format, self.s("blah"), "=12")

    def test_precision(self):
        assert format(self.s("abcdef"), ".3") == self.s("abc")

    def test_non_ascii_presentation(self):
        raises(ValueError, format, self.s(""), "\x234")



class AppTestUnicodeFormat(BaseStringFormatTests):

    def setup_class(cls):
        cls.w_s = cls.space.w_unicode

    def test_string_conversion(self):
        class x(object):
            def __repr__(self):
                return "32"
            def __str__(self):
                return "18"
            def __unicode__(self):
                return "42"
        assert self.s("{!s}").format(x()) == self.s("42")
        assert self.s("{!r}").format(x()) == self.s("32")

    def test_non_latin1_key(self):
        raises(KeyError, self.s("{\u1000}").format)



class AppTestStringFormat(BaseStringFormatTests):

    def setup_class(cls):
        cls.w_s = cls.space.w_str

    def test_string_conversion(self):
        class x(object):
            def __repr__(self):
                return "32"
            def __str__(self):
                return "18"
            def __unicode__(self):
                return "42"
        assert self.s("{!s}").format(x()) == self.s("18")
        assert self.s("{!r}").format(x()) == self.s("32")


class BaseIntegralFormattingTest:

    def test_simple(self):
        assert format(self.i(2)) == "2"
        assert isinstance(format(self.i(2), u""), unicode)

    def test_invalid(self):
        raises(ValueError, format, self.i(8), "s")
        raises(ValueError, format, self.i(8), ".3")

    def test_c(self):
        a = self.i(ord("a"))
        assert format(a, "c") == "a"
        as_uni = format(a, u"c")
        assert as_uni == u"a"
        assert isinstance(as_uni, unicode)
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


class AppTestLongFormatting(BaseIntegralFormattingTest):

    def setup_class(cls):
        cls.w_i = cls.space.w_long


class AppTestFloatFormatting:

    def test_alternate(self):
        raises(ValueError, format, 1.0, "#")

    def test_simple(self):
        assert format(0.0, "f") == "0.000000"

    def test_sign(self):
        assert format(-1.23, "1") == "-1.23"

    def test_digit_separator(self):
        assert format(-1234., "012,f") == "-1,234.000000"

    def test_dont_switch_to_g(self):
        skip("must fix when float formatting is figured out")
        assert len(format(1.1234e90, "f")) == 98
