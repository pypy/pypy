"""
String formatting routines.
"""
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rlib.rfloat import formatd, DTSF_ALT, isnan, isinf
from pypy.interpreter.error import OperationError
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder
from pypy.objspace.std.unicodetype import unicode_from_object

class BaseStringFormatter(object):
    def __init__(self, space, values_w, w_valuedict):
        self.space = space
        self.fmtpos = 0
        self.values_w = values_w
        self.values_pos = 0
        self.w_valuedict = w_valuedict

    def forward(self):
        # move current position forward
        self.fmtpos += 1

    def nextinputvalue(self):
        # return the next value in the tuple of input arguments
        try:
            w_result = self.values_w[self.values_pos]
        except IndexError:
            space = self.space
            raise OperationError(space.w_TypeError, space.wrap(
                'not enough arguments for format string'))
        else:
            self.values_pos += 1
            return w_result

    def checkconsumed(self):
        if self.values_pos < len(self.values_w) and self.w_valuedict is None:
            space = self.space
            raise OperationError(space.w_TypeError,
               space.wrap('not all arguments converted '
                            'during string formatting'))

    def std_wp_int(self, r, prefix='', keep_zero=False):
        # use self.prec to add some '0' on the left of the number
        if self.prec >= 0:
            if self.prec > 1000:
                raise OperationError(
                    self.space.w_OverflowError, self.space.wrap(
                    'formatted integer is too long (precision too large?)'))
            sign = r[0] == '-'
            padding = self.prec - (len(r)-int(sign))
            if padding > 0:
                if sign:
                    r = '-' + '0'*padding + r[1:]
                else:
                    r = '0'*padding + r
            elif self.prec == 0 and r == '0' and not keep_zero:
                r = ''
        self.std_wp_number(r, prefix)

    def fmt_d(self, w_value):
        "int formatting"
        r = int_num_helper(self.space, w_value)
        self.std_wp_int(r)

    def fmt_x(self, w_value):
        "hex formatting"
        r = hex_num_helper(self.space, w_value)
        if self.f_alt:
            prefix = '0x'
        else:
            prefix = ''
        self.std_wp_int(r, prefix)

    def fmt_X(self, w_value):
        "HEX formatting"
        r = hex_num_helper(self.space, w_value)
        if self.f_alt:
            prefix = '0X'
        else:
            prefix = ''
        self.std_wp_int(r.upper(), prefix)

    def fmt_o(self, w_value):
        "oct formatting"
        r = oct_num_helper(self.space, w_value)
        keep_zero = False
        if self.f_alt:
            if r == '0':
                keep_zero = True
            elif r.startswith('-'):
                r = '-0' + r[1:]
            else:
                r = '0' + r
        self.std_wp_int(r, keep_zero=keep_zero)

    fmt_i = fmt_d
    fmt_u = fmt_d

    def fmt_e(self, w_value):
        self.format_float(w_value, 'e')

    def fmt_f(self, w_value):
        self.format_float(w_value, 'f')

    def fmt_g(self, w_value):
        self.format_float(w_value, 'g')

    def fmt_E(self, w_value):
        self.format_float(w_value, 'E')

    def fmt_F(self, w_value):
        self.format_float(w_value, 'F')

    def fmt_G(self, w_value):
        self.format_float(w_value, 'G')

    def format_float(self, w_value, char):
        space = self.space
        x = space.float_w(maybe_float(space, w_value))
        if isnan(x):
            if char in 'EFG':
                r = 'NAN'
            else:
                r = 'nan'
        elif isinf(x):
            if x < 0:
                if char in 'EFG':
                    r = '-INF'
                else:
                    r = '-inf'
            else:
                if char in 'EFG':
                    r = 'INF'
                else:
                    r = 'inf'
        else:
            prec = self.prec
            if prec < 0:
                prec = 6
            if char in 'fF' and x/1e25 > 1e25:
                char = chr(ord(char) + 1)     # 'f' => 'g'
            flags = 0
            if self.f_alt:
                flags |= DTSF_ALT
            r = formatd(x, char, prec, flags)
        self.std_wp_number(r)

    def std_wp_number(self, r, prefix=''):
        raise NotImplementedError

def make_formatter_subclass(do_unicode):
    # to build two subclasses of the BaseStringFormatter class,
    # each one getting its own subtle differences and RPython types.

    if do_unicode:
        const = unicode
    else:
        const = str

    class StringFormatter(BaseStringFormatter):

        def __init__(self, space, fmt, values_w, w_valuedict):
            BaseStringFormatter.__init__(self, space, values_w, w_valuedict)
            self.fmt = fmt    # either a string or a unicode

        def peekchr(self):
            # return the 'current' character
            try:
                return self.fmt[self.fmtpos]
            except IndexError:
                space = self.space
                raise OperationError(space.w_ValueError,
                                     space.wrap("incomplete format"))

        def getmappingkey(self):
            # return the mapping key in a '%(key)s' specifier
            fmt = self.fmt
            i = self.fmtpos + 1   # first character after '('
            i0 = i
            pcount = 1
            while 1:
                try:
                    c = fmt[i]
                except IndexError:
                    space = self.space
                    raise OperationError(space.w_ValueError,
                                         space.wrap("incomplete format key"))
                if c == ')':
                    pcount -= 1
                    if pcount == 0:
                        break
                elif c == '(':
                    pcount += 1
                i += 1
            self.fmtpos = i + 1   # first character after ')'
            return fmt[i0:i]

        def getmappingvalue(self, key):
            # return the value corresponding to a key in the input dict
            space = self.space
            if self.w_valuedict is None:
                raise OperationError(space.w_TypeError,
                                     space.wrap("format requires a mapping"))
            w_key = space.wrap(key)
            return space.getitem(self.w_valuedict, w_key)

        def parse_fmt(self):
            if self.peekchr() == '(':
                w_value = self.getmappingvalue(self.getmappingkey())
            else:
                w_value = None

            self.peel_flags()

            self.width = self.peel_num()
            if self.width < 0:
                # this can happen:  '%*s' % (-5, "hi")
                self.f_ljust = True
                self.width = -self.width

            if self.peekchr() == '.':
                self.forward()
                self.prec = self.peel_num()
                if self.prec < 0:
                    self.prec = 0    # this can happen:  '%.*f' % (-5, 3)
            else:
                self.prec = -1

            c = self.peekchr()
            if c == 'h' or c == 'l' or c == 'L':
                self.forward()

            return w_value

        def peel_flags(self):
            self.f_ljust = False
            self.f_sign  = False
            self.f_blank = False
            self.f_alt   = False
            self.f_zero  = False
            while True:
                c = self.peekchr()
                if c == '-':
                    self.f_ljust = True
                elif c == '+':
                    self.f_sign = True
                elif c == ' ':
                    self.f_blank = True
                elif c == '#':
                    self.f_alt = True
                elif c == '0':
                    self.f_zero = True
                else:
                    break
                self.forward()

        def peel_num(self):
            space = self.space
            c = self.peekchr()
            if c == '*':
                self.forward()
                w_value = self.nextinputvalue()
                return space.int_w(maybe_int(space, w_value))
            result = 0
            while True:
                n = ord(c) - ord('0')
                if not (0 <= n < 10):
                    break
                try:
                    result = ovfcheck(ovfcheck(result * 10) + n)
                except OverflowError:
                    raise OperationError(space.w_OverflowError,
                                         space.wrap("precision too large"))
                self.forward()
                c = self.peekchr()
            return result

        def format(self):
            lgt = len(self.fmt) + 4 * len(self.values_w) + 10
            if do_unicode:
                result = UnicodeBuilder(lgt)
            else:
                result = StringBuilder(lgt)
            self.result = result
            while True:
                # fast path: consume as many characters as possible
                fmt = self.fmt
                i = i0 = self.fmtpos
                while i < len(fmt):
                    if fmt[i] == '%':
                        break
                    i += 1
                else:
                    result.append_slice(fmt, i0, len(fmt))
                    break     # end of 'fmt' string
                result.append_slice(fmt, i0, i)
                self.fmtpos = i + 1

                # interpret the next formatter
                w_value = self.parse_fmt()
                c = self.peekchr()
                self.forward()
                if c == '%':
                    self.std_wp(const('%'))
                    continue
                if w_value is None:
                    w_value = self.nextinputvalue()

                # dispatch on the formatter
                # (this turns into a switch after translation)
                for c1 in FORMATTER_CHARS:
                    if c == c1:
                        # 'c1' is an annotation constant here,
                        # so this getattr() is ok
                        do_fmt = getattr(self, 'fmt_' + c1)
                        do_fmt(w_value)
                        break
                else:
                    self.unknown_fmtchar()

            self.checkconsumed()
            return result.build()

        def unknown_fmtchar(self):
            space = self.space
            c = self.fmt[self.fmtpos - 1]
            if do_unicode:
                w_defaultencoding = space.call_function(
                    space.sys.get('getdefaultencoding'))
                w_s = space.call_method(space.wrap(c),
                                        "encode",
                                        w_defaultencoding,
                                        space.wrap('replace'))
                s = space.str_w(w_s)
            else:
                s = c
            msg = "unsupported format character '%s' (0x%x) at index %d" % (
                s, ord(c), self.fmtpos - 1)
            raise OperationError(space.w_ValueError, space.wrap(msg))

        def std_wp(self, r):
            length = len(r)
            if do_unicode and isinstance(r, str):
                # convert string to unicode explicitely here
                from pypy.objspace.std.unicodetype import plain_str2unicode
                r = plain_str2unicode(self.space, r)
            prec = self.prec
            if prec == -1 and self.width == 0:
                # fast path
                self.result.append(const(r))
                return
            if prec >= 0 and prec < length:
                length = prec   # ignore the end of the string if too long
            result = self.result
            padding = self.width - length
            if padding < 0:
                padding = 0
            assert padding >= 0
            if not self.f_ljust and padding > 0:
                result.append_multiple_char(const(' '), padding)
                # add any padding at the left of 'r'
                padding = 0
            result.append_slice(r, 0, length)       # add 'r' itself
            if padding > 0:
                result.append_multiple_char(const(' '), padding)
            # add any remaining padding at the right
        std_wp._annspecialcase_ = 'specialize:argtype(1)'

        def std_wp_number(self, r, prefix=''):
            # add a '+' or ' ' sign if necessary
            sign = r.startswith('-')
            if not sign:
                if self.f_sign:
                    r = '+' + r
                    sign = True
                elif self.f_blank:
                    r = ' ' + r
                    sign = True
            # do the padding requested by self.width and the flags,
            # without building yet another RPython string but directly
            # by pushing the pad character into self.result
            result = self.result
            padding = self.width - len(r) - len(prefix)
            if padding <= 0:
                padding = 0

            if self.f_ljust:
                padnumber = '<'
            elif self.f_zero:
                padnumber = '0'
            else:
                padnumber = '>'

            assert padding >= 0
            if padnumber == '>':
                result.append_multiple_char(const(' '), padding)
                # pad with spaces on the left
            if sign:
                result.append(const(r[0]))        # the sign
            result.append(const(prefix))               # the prefix
            if padnumber == '0':
                result.append_multiple_char(const('0'), padding)
                # pad with zeroes
            result.append_slice(const(r), int(sign), len(r))
            # the rest of the number
            if padnumber == '<':           # spaces on the right
                result.append_multiple_char(const(' '), padding)

        def string_formatting(self, w_value):
            space = self.space
            w_impl = space.lookup(w_value, '__str__')
            if w_impl is None:
                raise OperationError(space.w_TypeError,
                                     space.wrap("operand does not support "
                                                "unary str"))
            w_result = space.get_and_call_function(w_impl, w_value)
            if space.isinstance_w(w_result,
                                              space.w_unicode):
                raise NeedUnicodeFormattingError
            return space.str_w(w_result)

        def fmt_s(self, w_value):
            space = self.space
            got_unicode = space.isinstance_w(w_value,
                                                         space.w_unicode)
            if not do_unicode:
                if got_unicode:
                    raise NeedUnicodeFormattingError
                s = self.string_formatting(w_value)
            else:
                if not got_unicode:
                    w_value = space.call_function(space.w_unicode, w_value)
                else:
                    w_value = unicode_from_object(space, w_value)
                s = space.unicode_w(w_value)
            self.std_wp(s)

        def fmt_r(self, w_value):
            self.std_wp(self.space.str_w(self.space.repr(w_value)))

        def fmt_c(self, w_value):
            self.prec = -1     # just because
            space = self.space
            if space.isinstance_w(w_value, space.w_str):
                s = space.str_w(w_value)
                if len(s) != 1:
                    raise OperationError(space.w_TypeError,
                                         space.wrap("%c requires int or char"))
                self.std_wp(s)
            elif space.isinstance_w(w_value, space.w_unicode):
                if not do_unicode:
                    raise NeedUnicodeFormattingError
                ustr = space.unicode_w(w_value)
                if len(ustr) != 1:
                    raise OperationError(space.w_TypeError,
                                      space.wrap("%c requires int or unichar"))
                self.std_wp(ustr)
            else:
                n = space.int_w(w_value)
                if do_unicode:
                    try:
                        c = unichr(n)
                    except ValueError:
                        raise OperationError(space.w_OverflowError,
                            space.wrap("unicode character code out of range"))
                    self.std_wp(c)
                else:
                    try:
                        s = chr(n)
                    except ValueError:  # chr(out-of-range)
                        raise OperationError(space.w_OverflowError,
                            space.wrap("character code not in range(256)"))
                    self.std_wp(s)

    return StringFormatter


class NeedUnicodeFormattingError(Exception):
    pass

StringFormatter = make_formatter_subclass(do_unicode=False)
UnicodeFormatter = make_formatter_subclass(do_unicode=True)
UnicodeFormatter.__name__ = 'UnicodeFormatter'


# an "unrolling" list of all the known format characters,
# collected from which fmt_X() functions are defined in the class
FORMATTER_CHARS = unrolling_iterable(
    [_name[-1] for _name in dir(StringFormatter)
               if len(_name) == 5 and _name.startswith('fmt_')])

def format(space, w_fmt, values_w, w_valuedict=None, do_unicode=False):
    "Entry point"
    if not do_unicode:
        fmt = space.str_w(w_fmt)
        formatter = StringFormatter(space, fmt, values_w, w_valuedict)
        try:
            result = formatter.format()
        except NeedUnicodeFormattingError:
            # fall through to the unicode case
            from pypy.objspace.std.unicodetype import plain_str2unicode
            fmt = plain_str2unicode(space, fmt)
        else:
            return space.wrap(result)
    else:
        fmt = space.unicode_w(w_fmt)
    formatter = UnicodeFormatter(space, fmt, values_w, w_valuedict)
    result = formatter.format()
    return space.wrap(result)

def mod_format(space, w_format, w_values, do_unicode=False):
    if space.isinstance_w(w_values, space.w_tuple):
        values_w = space.fixedview(w_values)
        return format(space, w_format, values_w, None, do_unicode)
    else:
        # we check directly for dict to avoid obscure checking
        # in simplest case
        if space.isinstance_w(w_values, space.w_dict) or \
           (space.lookup(w_values, '__getitem__') and
           not space.isinstance_w(w_values, space.w_basestring)):
            return format(space, w_format, [w_values], w_values, do_unicode)
        else:
            return format(space, w_format, [w_values], None, do_unicode)

# ____________________________________________________________
# Formatting helpers

def maybe_int(space, w_value):
    # make sure that w_value is a wrapped integer
    return space.int(w_value)

def maybe_float(space, w_value):
    # make sure that w_value is a wrapped float
    return space.float(w_value)

def format_num_helper_generator(fmt, digits):
    def format_num_helper(space, w_value):
        w_value = maybe_int(space, w_value)
        try:
            value = space.int_w(w_value)
            return fmt % (value,)
        except OperationError, operr:
            if not operr.match(space, space.w_OverflowError):
                raise
            num = space.bigint_w(w_value)
            return num.format(digits)
    return func_with_new_name(format_num_helper,
                              'base%d_num_helper' % len(digits))

int_num_helper = format_num_helper_generator('%d', '0123456789')
oct_num_helper = format_num_helper_generator('%o', '01234567')
hex_num_helper = format_num_helper_generator('%x', '0123456789abcdef')
