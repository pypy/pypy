"""The unicode/str format() method"""

import string

from pypy.interpreter.error import OperationError
from pypy.rlib import rstring, runicode, rlocale, rarithmetic, rfloat
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rfloat import copysign, formatd


@specialize.argtype(1)
def _parse_int(space, s, start, end):
    """Parse a number and check for overflows"""
    result = 0
    i = start
    while i < end:
        c = ord(s[i])
        if ord("0") <= c <= ord("9"):
            try:
                result = rarithmetic.ovfcheck(result * 10)
            except OverflowError:
                msg = "too many decimal digits in format string"
                raise OperationError(space.w_ValueError, space.wrap(msg))
            result += c - ord("0")
        else:
            break
        i += 1
    if i == start:
        result = -1
    return result, i


# Auto number state
ANS_INIT = 1
ANS_AUTO = 2
ANS_MANUAL = 3


class TemplateFormatter(object):

    _annspecialcase_ = "specialize:ctr_location"

    parser_list_w = None

    def __init__(self, space, is_unicode, template):
        self.space = space
        self.is_unicode = is_unicode
        self.empty = u"" if is_unicode else ""
        self.template = template

    def build(self, args):
        self.args, self.kwargs = args.unpack()
        self.auto_numbering = 0
        self.auto_numbering_state = ANS_INIT
        return self._build_string(0, len(self.template), 2)

    def _build_string(self, start, end, level):
        space = self.space
        if self.is_unicode:
            out = rstring.UnicodeBuilder()
        else:
            out = rstring.StringBuilder()
        if not level:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Recursion depth exceeded"))
        level -= 1
        s = self.template
        last_literal = i = start
        while i < end:
            c = s[i]
            i += 1
            if c == "{" or c == "}":
                at_end = i == end
                # Find escaped "{" and "}"
                markup_follows = True
                if c == "}":
                    if at_end or s[i] != "}":
                        raise OperationError(space.w_ValueError,
                                             space.wrap("Single '}'"))
                    i += 1
                    markup_follows = False
                if c == "{":
                    if at_end:
                        raise OperationError(space.w_ValueError,
                                             space.wrap("Single '{'"))
                    if s[i] == "{":
                        i += 1
                        markup_follows = False
                # Attach literal data
                out.append_slice(s, last_literal, i - 1)
                if not markup_follows:
                    last_literal = i
                    continue
                nested = 1
                field_start = i
                recursive = False
                while i < end:
                    c = s[i]
                    if c == "{":
                        recursive = True
                        nested += 1
                    elif c == "}":
                        nested -= 1
                        if not nested:
                            break
                    i += 1
                if nested:
                    raise OperationError(space.w_ValueError,
                                         space.wrap("Unmatched '{'"))
                rendered = self._render_field(field_start, i, recursive, level)
                out.append(rendered)
                i += 1
                last_literal = i

        out.append_slice(s, last_literal, end)
        return out.build()

    def _parse_field(self, start, end):
        s = self.template
        # Find ":" or "!"
        i = start
        while i < end:
            c = s[i]
            if c == ":" or c == "!":
                end_name = i
                if c == "!":
                    i += 1
                    if i == end:
                        w_msg = self.space.wrap("expected conversion")
                        raise OperationError(self.space.w_ValueError, w_msg)
                    conversion = s[i]
                    i += 1
                    if i < end:
                        if s[i] != ':':
                            w_msg = self.space.wrap("expected ':' after"
                                                    " format specifier")
                            raise OperationError(self.space.w_ValueError,
                                                 w_msg)
                        i += 1
                else:
                    conversion = None
                    i += 1
                return s[start:end_name], conversion, i
            i += 1
        return s[start:end], None, end

    def _get_argument(self, name):
        # First, find the argument.
        space = self.space
        i = 0
        end = len(name)
        while i < end:
            c = name[i]
            if c == "[" or c == ".":
                break
            i += 1
        empty = not i
        if empty:
            index = -1
        else:
            index, stop = _parse_int(self.space, name, 0, i)
            if stop != i:
                index = -1
        use_numeric = empty or index != -1
        if self.auto_numbering_state == ANS_INIT and use_numeric:
            if empty:
                self.auto_numbering_state = ANS_AUTO
            else:
                self.auto_numbering_state = ANS_MANUAL
        if use_numeric:
            if self.auto_numbering_state == ANS_MANUAL:
                if empty:
                    msg = "switching from manual to automatic numbering"
                    raise OperationError(space.w_ValueError,
                                         space.wrap(msg))
            elif not empty:
                msg = "switching from automatic to manual numbering"
                raise OperationError(space.w_ValueError,
                                     space.wrap(msg))
        if empty:
            index = self.auto_numbering
            self.auto_numbering += 1
        if index == -1:
            kwarg = name[:i]
            if self.is_unicode:
                try:
                    arg_key = kwarg.encode("latin-1")
                except UnicodeEncodeError:
                    # Not going to be found in a dict of strings.
                    raise OperationError(space.w_KeyError, space.wrap(kwarg))
            else:
                arg_key = kwarg
            try:
                w_arg = self.kwargs[arg_key]
            except KeyError:
                raise OperationError(space.w_KeyError, space.wrap(arg_key))
        else:
            try:
                w_arg = self.args[index]
            except IndexError:
                w_msg = space.wrap("index out of range")
                raise OperationError(space.w_IndexError, w_msg)
        return self._resolve_lookups(w_arg, name, i, end)

    def _resolve_lookups(self, w_obj, name, start, end):
        # Resolve attribute and item lookups.
        space = self.space
        i = start
        while i < end:
            c = name[i]
            if c == ".":
                i += 1
                start = i
                while i < end:
                    c = name[i]
                    if c == "[" or c == ".":
                        break
                    i += 1
                if start == i:
                    w_msg = space.wrap("Empty attribute in format string")
                    raise OperationError(space.w_ValueError, w_msg)
                w_attr = space.wrap(name[start:i])
                if w_obj is not None:
                    w_obj = space.getattr(w_obj, w_attr)
                else:
                    self.parser_list_w.append(space.newtuple([
                        space.w_True, w_attr]))
            elif c == "[":
                got_bracket = False
                i += 1
                start = i
                while i < end:
                    c = name[i]
                    if c == "]":
                        got_bracket = True
                        break
                    i += 1
                if not got_bracket:
                    raise OperationError(space.w_ValueError,
                                         space.wrap("Missing ']'"))
                index, reached = _parse_int(self.space, name, start, i)
                if index != -1 and reached == i:
                    w_item = space.wrap(index)
                else:
                    w_item = space.wrap(name[start:i])
                i += 1 # Skip "]"
                if w_obj is not None:
                    w_obj = space.getitem(w_obj, w_item)
                else:
                    self.parser_list_w.append(space.newtuple([
                        space.w_False, w_item]))
            else:
                msg = "Only '[' and '.' may follow ']'"
                raise OperationError(space.w_ValueError, space.wrap(msg))
        return w_obj

    def formatter_field_name_split(self):
        space = self.space
        name = self.template
        i = 0
        end = len(name)
        while i < end:
            c = name[i]
            if c == "[" or c == ".":
                break
            i += 1
        if i == 0:
            index = -1
        else:
            index, stop = _parse_int(self.space, name, 0, i)
            if stop != i:
                index = -1
        if index >= 0:
            w_first = space.wrap(index)
        else:
            w_first = space.wrap(name[:i])
        #
        self.parser_list_w = []
        self._resolve_lookups(None, name, i, end)
        #
        return space.newtuple([w_first,
                               space.iter(space.newlist(self.parser_list_w))])

    def _convert(self, w_obj, conversion):
        space = self.space
        conv = conversion[0]
        if conv == "r":
            return space.repr(w_obj)
        elif conv == "s":
            if self.is_unicode:
                return space.call_function(space.w_unicode, w_obj)
            return space.str(w_obj)
        else:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap("invalid conversion"))

    def _render_field(self, start, end, recursive, level):
        name, conversion, spec_start = self._parse_field(start, end)
        spec = self.template[spec_start:end]
        #
        if self.parser_list_w is not None:
            # used from formatter_parser()
            if level == 1:    # ignore recursive calls
                space = self.space
                startm1 = start - 1
                assert startm1 >= self.last_end
                w_entry = space.newtuple([
                    space.wrap(self.template[self.last_end:startm1]),
                    space.wrap(name),
                    space.wrap(spec),
                    space.wrap(conversion)])
                self.parser_list_w.append(w_entry)
                self.last_end = end + 1
            return self.empty
        #
        w_obj = self._get_argument(name)
        if conversion is not None:
            w_obj = self._convert(w_obj, conversion)
        if recursive:
            spec = self._build_string(spec_start, end, level)
        w_rendered = self.space.format(w_obj, self.space.wrap(spec))
        unwrapper = "unicode_w" if self.is_unicode else "str_w"
        to_interp = getattr(self.space, unwrapper)
        return to_interp(w_rendered)

    def formatter_parser(self):
        self.parser_list_w = []
        self.last_end = 0
        self._build_string(0, len(self.template), 2)
        #
        space = self.space
        if self.last_end < len(self.template):
            w_lastentry = space.newtuple([
                space.wrap(self.template[self.last_end:]),
                space.w_None,
                space.w_None,
                space.w_None])
            self.parser_list_w.append(w_lastentry)
        return space.iter(space.newlist(self.parser_list_w))


def str_template_formatter(space, template):
    return TemplateFormatter(space, False, template)

def unicode_template_formatter(space, template):
    return TemplateFormatter(space, True, template)


def format_method(space, w_string, args, is_unicode):
    if is_unicode:
        template = unicode_template_formatter(space,
                                              space.unicode_w(w_string))
        return space.wrap(template.build(args))
    else:
        template = str_template_formatter(space, space.str_w(w_string))
        return space.wrap(template.build(args))


class NumberSpec(object):
    pass

class BaseFormatter(object):

    def format_int_or_long(self, w_num, kind):
        raise NotImplementedError

    def format_float(self, w_num):
        raise NotImplementedError

    def format_complex(self, w_num):
        raise NotImplementedError


INT_KIND = 1
LONG_KIND = 2

NO_LOCALE = 1
DEFAULT_LOCALE = 2
CURRENT_LOCALE = 3

LONG_DIGITS = string.digits + string.ascii_lowercase

class Formatter(BaseFormatter):
    """__format__ implementation for builtin types."""

    _annspecialcase_ = "specialize:ctr_location"
    _grouped_digits = None

    def __init__(self, space, is_unicode, spec):
        self.space = space
        self.is_unicode = is_unicode
        self.empty = u"" if is_unicode else ""
        self.spec = spec

    def _is_alignment(self, c):
        return (c == "<" or
                c == ">" or
                c == "=" or
                c == "^")

    def _is_sign(self, c):
        return (c == " " or
                c == "+" or
                c == "-")

    def _parse_spec(self, default_type, default_align):
        space = self.space
        self._fill_char = self._lit("\0")[0]
        self._align = default_align
        self._alternate = False
        self._sign = "\0"
        self._thousands_sep = False
        self._precision = -1
        the_type = default_type
        spec = self.spec
        if not spec:
            return True
        length = len(spec)
        i = 0
        got_align = True
        if length - i >= 2 and self._is_alignment(spec[i + 1]):
            self._align = spec[i + 1]
            self._fill_char = spec[i]
            i += 2
        elif length - i >= 1 and self._is_alignment(spec[i]):
            self._align = spec[i]
            i += 1
        else:
            got_align = False
        if length - i >= 1 and self._is_sign(spec[i]):
            self._sign = spec[i]
            i += 1
        if length - i >= 1 and spec[i] == "#":
            self._alternate = True
            i += 1
        if self._fill_char == "\0" and length - i >= 1 and spec[i] == "0":
            self._fill_char = self._lit("0")[0]
            if not got_align:
                self._align = "="
            i += 1
        start_i = i
        self._width, i = _parse_int(self.space, spec, i, length)
        if length != i and spec[i] == ",":
            self._thousands_sep = True
            i += 1
        if length != i and spec[i] == ".":
            i += 1
            self._precision, i = _parse_int(self.space, spec, i, length)
            if self._precision == -1:
                raise OperationError(space.w_ValueError,
                                     space.wrap("no precision given"))
        if length - i > 1:
            raise OperationError(space.w_ValueError,
                                 space.wrap("invalid format spec"))
        if length - i == 1:
            presentation_type = spec[i]
            if self.is_unicode:
                try:
                    the_type = spec[i].encode("ascii")[0]
                except UnicodeEncodeError:
                    raise OperationError(space.w_ValueError,
                                         space.wrap("invalid presentation type"))
            else:
                the_type = presentation_type
            i += 1
        self._type = the_type
        if self._thousands_sep:
            tp = self._type
            if (tp == "d" or
                tp == "e" or
                tp == "f" or
                tp == "g" or
                tp == "E" or
                tp == "G" or
                tp == "%" or
                tp == "F" or
                tp == "\0"):
                # ok
                pass
            else:
                raise OperationError(space.w_ValueError,
                                     space.wrap("invalid type with ','"))
        return False

    def _calc_padding(self, string, length):
        """compute left and right padding, return total width of string"""
        if self._width != -1 and length < self._width:
            total = self._width
        else:
            total = length
        align = self._align
        if align == ">":
            left = total - length
        elif align == "^":
            left = (total - length) / 2
        elif align == "<" or align == "=":
            left = 0
        else:
            raise AssertionError("shouldn't be here")
        right = total - length - left
        self._left_pad = left
        self._right_pad = right
        return total

    def _lit(self, s):
        if self.is_unicode:
            return s.decode("ascii")
        else:
            return s

    def _pad(self, string):
        builder = self._builder()
        builder.append_multiple_char(self._fill_char, self._left_pad)
        builder.append(string)
        builder.append_multiple_char(self._fill_char, self._right_pad)
        return builder.build()

    def _builder(self):
        if self.is_unicode:
            return rstring.UnicodeBuilder()
        else:
            return rstring.StringBuilder()

    def _unknown_presentation(self, tp):
        msg = "unknown presentation for %s: '%s'"
        w_msg = self.space.wrap(msg  % (tp, self._type))
        raise OperationError(self.space.w_ValueError, w_msg)

    def format_string(self, string):
        space = self.space
        if self._parse_spec("s", "<"):
            return space.wrap(string)
        if self._type != "s":
            self._unknown_presentation("string")
        if self._sign != "\0":
            msg = "Sign not allowed in string format specifier"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        if self._alternate:
            msg = "Alternate form not allowed in string format specifier"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        if self._align == "=":
            msg = "'=' alignment not allowed in string format specifier"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        length = len(string)
        precision = self._precision
        if precision != -1 and length >= precision:
            assert precision >= 0
            length = precision
            string = string[:precision]
        if self._fill_char == "\0":
            self._fill_char = self._lit(" ")[0]
        self._calc_padding(string, length)
        return space.wrap(self._pad(string))

    def _get_locale(self, tp):
        space = self.space
        if tp == "n":
            dec, thousands, grouping = rlocale.numeric_formatting()
        elif self._thousands_sep:
            dec = "."
            thousands = ","
            grouping = "\3\0"
        else:
            dec = "."
            thousands = ""
            grouping = "\256"
        if self.is_unicode:
            self._loc_dec = dec.decode("ascii")
            self._loc_thousands = thousands.decode("ascii")
        else:
            self._loc_dec = dec
            self._loc_thousands = thousands
        self._loc_grouping = grouping

    def _calc_num_width(self, n_prefix, sign_char, to_number, n_number,
                        n_remainder, has_dec, digits):
        """Calculate widths of all parts of formatted number.

        Output will look like:

            <lpadding> <sign> <prefix> <spadding> <grouped_digits> <decimal>
            <remainder> <rpadding>

        sign is computed from self._sign, and the sign of the number
        prefix is given
        digits is known
        """
        spec = NumberSpec()
        spec.n_digits = n_number - n_remainder - has_dec
        spec.n_prefix = n_prefix
        spec.n_lpadding = 0
        spec.n_decimal = int(has_dec)
        spec.n_remainder = n_remainder
        spec.n_spadding = 0
        spec.n_rpadding = 0
        spec.n_min_width = 0
        spec.n_total = 0
        spec.sign = "\0"
        spec.n_sign = 0
        sign = self._sign
        if sign == "+":
            spec.n_sign = 1
            spec.sign = "-" if sign_char == "-" else "+"
        elif sign == " ":
            spec.n_sign = 1
            spec.sign = "-" if sign_char == "-" else " "
        elif sign_char == "-":
            spec.n_sign = 1
            spec.sign = "-"
        extra_length = (spec.n_sign + spec.n_prefix + spec.n_decimal +
                        spec.n_remainder) # Not padding or digits
        if self._fill_char == "0" and self._align == "=":
            spec.n_min_width = self._width - extra_length
        if self._loc_thousands:
            self._group_digits(spec, digits[to_number:])
            n_grouped_digits = len(self._grouped_digits)
        else:
            n_grouped_digits = spec.n_digits
        n_padding = self._width - (extra_length + n_grouped_digits)
        if n_padding > 0:
            align = self._align
            if align == "<":
                spec.n_rpadding = n_padding
            elif align == ">":
                spec.n_lpadding = n_padding
            elif align == "^":
                spec.n_lpadding = n_padding // 2
                spec.n_rpadding = n_padding - spec.n_lpadding
            elif align == "=":
                spec.n_spadding = n_padding
            else:
                raise AssertionError("shouldn't reach")
        spec.n_total = spec.n_lpadding + spec.n_sign + spec.n_prefix + \
                       spec.n_spadding + n_grouped_digits + \
                       spec.n_decimal + spec.n_remainder + spec.n_rpadding
        return spec

    def _fill_digits(self, buf, digits, d_state, n_chars, n_zeros,
                     thousands_sep):
        if thousands_sep:
            for c in thousands_sep:
                buf.append(c)
        for i in range(d_state - 1, d_state - n_chars - 1, -1):
            buf.append(digits[i])
        for i in range(n_zeros):
            buf.append("0")

    def _group_digits(self, spec, digits):
        buf = []
        grouping = self._loc_grouping
        min_width = spec.n_min_width
        grouping_state = 0
        count = 0
        left = spec.n_digits
        n_ts = len(self._loc_thousands)
        need_separator = False
        done = False
        groupings = len(grouping)
        previous = 0
        while True:
            group = ord(grouping[grouping_state])
            if group > 0:
                if group == 256:
                    break
                grouping_state += 1
                previous = group
            else:
                group = previous
            final_grouping = min(group, max(left, max(min_width, 1)))
            n_zeros = max(0, final_grouping - left)
            n_chars = max(0, min(left, final_grouping))
            ts = self._loc_thousands if need_separator else None
            self._fill_digits(buf, digits, left, n_chars, n_zeros, ts)
            need_separator = True
            left -= n_chars
            min_width -= final_grouping
            if left <= 0 and min_width <= 0:
                done = True
                break
            min_width -= n_ts
        if not done:
            group = max(max(left, min_width), 1)
            n_zeros = max(0, group - left)
            n_chars = max(0, min(left, group))
            ts = self._loc_thousands if need_separator else None
            self._fill_digits(buf, digits, left, n_chars, n_zeros, ts)
        buf.reverse()
        self._grouped_digits = self.empty.join(buf)

    def _upcase_string(self, s):
        buf = []
        for c in s:
            index = ord(c)
            if ord("a") <= index <= ord("z"):
                c = chr(index - 32)
            buf.append(c)
        return self.empty.join(buf)


    def _fill_number(self, spec, num, to_digits, to_prefix, fill_char,
                     to_remainder, upper, grouped_digits=None):
        out = self._builder()
        if spec.n_lpadding:
            out.append_multiple_char(fill_char[0], spec.n_lpadding)
        if spec.n_sign:
            if self.is_unicode:
                sign = spec.sign.decode("ascii")
            else:
                sign = spec.sign
            out.append(sign)
        if spec.n_prefix:
            pref = num[to_prefix:to_prefix + spec.n_prefix]
            if upper:
                pref = self._upcase_string(pref)
            out.append(pref)
        if spec.n_spadding:
            out.append_multiple_char(fill_char[0], spec.n_spadding)
        if spec.n_digits != 0:
            if self._loc_thousands:
                if grouped_digits is not None:
                    digits = grouped_digits
                else:
                    digits = self._grouped_digits
                    assert digits is not None
            else:
                stop = to_digits + spec.n_digits
                assert stop >= 0
                digits = num[to_digits:stop]
            if upper:
                digits = self._upcase_string(digits)
            out.append(digits)
        if spec.n_decimal:
            out.append(self._lit(".")[0])
        if spec.n_remainder:
            out.append(num[to_remainder:])
        if spec.n_rpadding:
            out.append_multiple_char(fill_char[0], spec.n_rpadding)
        #if complex, need to call twice - just retun the buffer
        return out.build()

    def _format_int_or_long(self, w_num, kind):
        space = self.space
        if self._precision != -1:
            msg = "precision not allowed in integer type"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        sign_char = "\0"
        tp = self._type
        if tp == "c":
            if self._sign != "\0":
                msg = "sign not allowed with 'c' presentation type"
                raise OperationError(space.w_ValueError, space.wrap(msg))
            value = space.int_w(w_num)
            if self.is_unicode:
                result = runicode.UNICHR(value)
            else:
                result = chr(value)
            n_digits = 1
            n_remainder = 1
            to_remainder = 0
            n_prefix = 0
            to_prefix = 0
            to_numeric = 0
        else:
            if tp == "b":
                base = 2
                skip_leading = 2
            elif tp == "o":
                base = 8
                skip_leading = 2
            elif tp == "x" or tp == "X":
                base = 16
                skip_leading = 2
            elif tp == "n" or tp == "d":
                base = 10
                skip_leading = 0
            else:
                raise AssertionError("shouldn't reach")
            if kind == INT_KIND:
                result = self._int_to_base(base, space.int_w(w_num))
            else:
                result = self._long_to_base(base, space.bigint_w(w_num))
            n_prefix = skip_leading if self._alternate else 0
            to_prefix = 0
            if result[0] == "-":
                sign_char = "-"
                skip_leading += 1
                to_prefix += 1
            n_digits = len(result) - skip_leading
            n_remainder = 0
            to_remainder = 0
            to_numeric = skip_leading
        self._get_locale(tp)
        spec = self._calc_num_width(n_prefix, sign_char, to_numeric, n_digits,
                                    n_remainder, False, result)
        fill = self._lit(" ") if self._fill_char == "\0" else self._fill_char
        upper = self._type == "X"
        return self.space.wrap(self._fill_number(spec, result, to_numeric,
                                 to_prefix, fill, to_remainder, upper))

    def _long_to_base(self, base, value):
        prefix = ""
        if base == 2:
            prefix = "0b"
        elif base == 8:
            prefix = "0o"
        elif base == 16:
            prefix = "0x"
        as_str = value.format(LONG_DIGITS[:base], prefix)
        if self.is_unicode:
            return as_str.decode("ascii")
        return as_str

    def _int_to_base(self, base, value):
        if base == 10:
            s = str(value)
            if self.is_unicode:
                return s.decode("ascii")
            return s
        # This part is slow.
        negative = value < 0
        value = abs(value)
        buf = ["\0"] * (8 * 8 + 6) # Too much on 32 bit, but who cares?
        i = len(buf) - 1
        while True:
            div = value // base
            mod = value - div * base
            digit = abs(mod)
            digit += ord("0") if digit < 10 else ord("a") - 10
            buf[i] = chr(digit)
            value = div
            i -= 1
            if not value:
                break
        if base == 2:
            buf[i] = "b"
            buf[i - 1] = "0"
        elif base == 8:
            buf[i] = "o"
            buf[i - 1] = "0"
        elif base == 16:
            buf[i] = "x"
            buf[i - 1] = "0"
        else:
            buf[i] = "#"
            buf[i - 1] = chr(ord("0") + base % 10)
            if base > 10:
                buf[i - 2] = chr(ord("0") + base // 10)
                i -= 1
        i -= 1
        if negative:
            i -= 1
            buf[i] = "-"
        assert i >= 0
        return self.empty.join(buf[i:])

    def format_int_or_long(self, w_num, kind):
        space = self.space
        if self._parse_spec("d", ">"):
            if self.is_unicode:
                return space.call_function(space.w_unicode, w_num)
            return self.space.str(w_num)
        tp = self._type
        if (tp == "b" or
            tp == "c" or
            tp == "d" or
            tp == "o" or
            tp == "x" or
            tp == "X" or
            tp == "n"):
            return self._format_int_or_long(w_num, kind)
        elif (tp == "e" or
              tp == "E" or
              tp == "f" or
              tp == "F" or
              tp == "g" or
              tp == "G" or
              tp == "%"):
            w_float = space.float(w_num)
            return self._format_float(w_float)
        else:
            self._unknown_presentation("int" if kind == INT_KIND else "long")

    def _parse_number(self, s, i):
        """Determine if s has a decimal point, and the index of the first #
        after the decimal, or the end of the number."""
        length = len(s)
        while i < length and "0" <= s[i] <= "9":
            i += 1
        rest = i
        dec_point = i < length and s[i] == "."
        if dec_point:
            rest += 1
        #differs from CPython method - CPython sets n_remainder
        return dec_point, rest

    def _format_float(self, w_float):
        """helper for format_float"""
        space = self.space
        flags = 0
        default_precision = 6
        if self._alternate:
            msg = "alternate form not allowed in float formats"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        tp = self._type
        self._get_locale(tp)
        if tp == "\0":
            tp = "g"
            default_precision = 12
            flags |= rfloat.DTSF_ADD_DOT_0
        elif tp == "n":
            tp = "g"
        value = space.float_w(w_float)
        if tp == "%":
            tp = "f"
            value *= 100
            add_pct = True
        else:
            add_pct = False
        if self._precision == -1:
            self._precision = default_precision
        result, special = rfloat.double_to_string(value, tp,
                                                  self._precision, flags)
        if add_pct:
            result += "%"
        n_digits = len(result)
        if result[0] == "-":
            sign = "-"
            to_number = 1
            n_digits -= 1
        else:
            sign = "\0"
            to_number = 0
        have_dec_point, to_remainder = self._parse_number(result, to_number)
        n_remainder = len(result) - to_remainder
        if self.is_unicode:
            digits = result.decode("ascii")
        else:
            digits = result
        spec = self._calc_num_width(0, sign, to_number, n_digits,
                                    n_remainder, have_dec_point, digits)
        fill = self._lit(" ") if self._fill_char == "\0" else self._fill_char
        return self.space.wrap(self._fill_number(spec, digits, to_number, 0,
                                  fill, to_remainder, False))

    def format_float(self, w_float):
        space = self.space
        if self._parse_spec("\0", ">"):
            if self.is_unicode:
                return space.call_function(space.w_unicode, w_float)
            return space.str(w_float)
        tp = self._type
        if (tp == "\0" or
            tp == "e" or
            tp == "E" or
            tp == "f" or
            tp == "F" or
            tp == "g" or
            tp == "G" or
            tp == "n" or
            tp == "%"):
            return self._format_float(w_float)
        self._unknown_presentation("float")

    def _format_complex(self, w_complex):
        space = self.space
        tp = self._type
        self._get_locale(tp)
        default_precision = 6
        if self._align == "=":
            # '=' alignment is invalid
            msg = ("'=' alignment flag is not allowed in"
                   " complex format specifier")
            raise OperationError(space.w_ValueError, space.wrap(msg))
        if self._fill_char == "0":
            #zero padding is invalid
            msg = "Zero padding is not allowed in complex format specifier"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        if self._alternate:
            #alternate is invalid
            msg = "Alternate form %s not allowed in complex format specifier"
            raise OperationError(space.w_ValueError,
                                 space.wrap(msg % (self._alternate)))
        skip_re = 0
        add_parens = 0
        if tp == "\0":
            #should mirror str() output
            tp = "g"
            default_precision = 12
            #test if real part is non-zero
            if (w_complex.realval == 0 and
                copysign(1., w_complex.realval) == 1.):
                skip_re = 1
            else:
                add_parens = 1

        if tp == "n":
            #same as 'g' except for locale, taken care of later
            tp = "g"

        #check if precision not set
        if self._precision == -1:
            self._precision = default_precision

        #might want to switch to double_to_string from formatd
        #in CPython it's named 're' - clashes with re module
        re_num = formatd(w_complex.realval, tp, self._precision)
        im_num = formatd(w_complex.imagval, tp, self._precision)
        n_re_digits = len(re_num)
        n_im_digits = len(im_num)

        to_real_number = 0
        to_imag_number = 0
        re_sign = im_sign = ''
        #if a sign character is in the output, remember it and skip
        if re_num[0] == "-":
            re_sign = "-"
            to_real_number = 1
            n_re_digits -= 1
        if im_num[0] == "-":
            im_sign = "-"
            to_imag_number = 1
            n_im_digits -= 1

        #turn off padding - do it after number composition
        #calc_num_width uses self._width, so assign to temporary variable,
        #calculate width of real and imag parts, then reassign padding, align
        tmp_fill_char = self._fill_char
        tmp_align = self._align
        tmp_width = self._width
        self._fill_char = "\0"
        self._align = "<"
        self._width = -1

        #determine if we have remainder, might include dec or exponent or both
        re_have_dec, re_remainder_ptr = self._parse_number(re_num,
                                                           to_real_number)
        im_have_dec, im_remainder_ptr = self._parse_number(im_num,
                                                           to_imag_number)

        if self.is_unicode:
            re_num = re_num.decode("ascii")
            im_num = im_num.decode("ascii")

        #set remainder, in CPython _parse_number sets this
        #using n_re_digits causes tests to fail
        re_n_remainder = len(re_num) - re_remainder_ptr
        im_n_remainder = len(im_num) - im_remainder_ptr
        re_spec = self._calc_num_width(0, re_sign, to_real_number, n_re_digits,
                                       re_n_remainder, re_have_dec,
                                       re_num)

        #capture grouped digits b/c _fill_number reads from self._grouped_digits
        #self._grouped_digits will get overwritten in imaginary calc_num_width
        re_grouped_digits = self._grouped_digits
        if not skip_re:
            self._sign = "+"
        im_spec = self._calc_num_width(0, im_sign, to_imag_number, n_im_digits,
                                       im_n_remainder, im_have_dec,
                                       im_num)

        im_grouped_digits = self._grouped_digits
        if skip_re:
            re_spec.n_total = 0

        #reassign width, alignment, fill character
        self._align = tmp_align
        self._width = tmp_width
        self._fill_char = tmp_fill_char

        #compute L and R padding - stored in self._left_pad and self._right_pad
        self._calc_padding(self.empty, re_spec.n_total + im_spec.n_total + 1 +
                                       add_parens * 2)

        out = self._builder()
        fill = self._fill_char
        if fill == "\0":
            fill = self._lit(" ")[0]

        #compose the string
        #add left padding
        out.append_multiple_char(fill, self._left_pad)
        if add_parens:
            out.append(self._lit('(')[0])

        #if the no. has a real component, add it
        if not skip_re:
            out.append(self._fill_number(re_spec, re_num, to_real_number, 0,
                                         fill, re_remainder_ptr, False,
                                         re_grouped_digits))

        #add imaginary component
        out.append(self._fill_number(im_spec, im_num, to_imag_number, 0,
                                     fill, im_remainder_ptr, False,
                                     im_grouped_digits))

        #add 'j' character
        out.append(self._lit('j')[0])

        if add_parens:
            out.append(self._lit(')')[0])

        #add right padding
        out.append_multiple_char(fill, self._right_pad)

        return self.space.wrap(out.build())


    def format_complex(self, w_complex):
        """return the string representation of a complex number"""
        space = self.space
        #parse format specification, set associated variables
        if self._parse_spec("\0", ">"):
            return space.str(w_complex)
        tp = self._type
        if (tp == "\0" or
            tp == "e" or
            tp == "E" or
            tp == "f" or
            tp == "F" or
            tp == "g" or
            tp == "G" or
            tp == "n"):
            return self._format_complex(w_complex)
        self._unknown_presentation("complex")


def unicode_formatter(space, spec):
    return Formatter(space, True, spec)


def str_formatter(space, spec):
    return Formatter(space, False, spec)


@specialize.arg(2)
def run_formatter(space, w_format_spec, meth, *args):
    if space.isinstance_w(w_format_spec, space.w_unicode):
        formatter = unicode_formatter(space, space.unicode_w(w_format_spec))
        return getattr(formatter, meth)(*args)
    else:
        formatter = str_formatter(space, space.str_w(w_format_spec))
        return getattr(formatter, meth)(*args)
