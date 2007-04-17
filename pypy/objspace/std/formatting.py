
# Application level implementation of string formatting.

# There's some insane stuff in here.  Blame CPython.  Please.

# Known problems:
# (1) rounding isn't always right (see comments in _float_formatting).
# (2) something goes wrong in the f_alt case of %g handling.
# (3) it's really, really slow.
#
# XXX regarding moving the below code to RPython (mostly):
#     ValueGetter and ValueBox were introduced to encapsulate
#     dealing with (wrapped/unwrapped) values.  The rest
#     of the source code appears to be rather RPython except
#     for the usage of rpython-level unicode strings. 


import sys
from pypy.interpreter.error import OperationError, debug_print
from pypy.rlib import rarithmetic

class _Flags(object):
    def __repr__(self):
        return "<%s>"%(', '.join([f for f in self.__dict__
                                  if f[0] == 'f' and getattr(self, f)]),)
    f_ljust = 0
    f_sign = 0
    f_blank = 0
    f_alt = 0
    f_zero = 0


def peel_num(space, c, fmtiter, valuegetter):
    if c == '*':
        v = valuegetter.nextvalue()
        if not v.isint():
            raise OperationError(space.w_TypeError, space.wrap("* wants int"))
        return fmtiter.next(), space.int_w(v.maybe_int())
    i0 = fmtiter.i - 1
    assert i0 > 0
    ik = i0
    while c in '0123456789':
        c = fmtiter.next()
        ik += 1
    if ik != i0:
        return c, int(fmtiter.fmt[i0:ik])
    else:
        return c, 0


def peel_flags(c, fmtiter):
    flags = _Flags()
    while 1:
        if c == '-':
            flags.f_ljust = True
        elif c == '+':
            flags.f_sign = True
        elif c == ' ':
            flags.f_blank = True
        elif c == '#':
            flags.f_alt = True
        elif c == '0':
            flags.f_zero = True
        else:
            break
        c = fmtiter.next()
    return c, flags


def parse_fmt(space, fmtiter, valuegetter):
    """return (char, flags, width, prec, value)
    partially consumes fmtiter & valuegetter"""
    c = fmtiter.next()
    value = None
    gotvalue = False
    if c == '(':
        i0 = fmtiter.i
        assert i0 > 0
        ik = i0
        pcount = 1
        while 1:
            c = fmtiter.next()
            if c == ')':
                pcount -= 1
                if pcount == 0:
                    break
            elif c == '(':
                pcount += 1
            ik += 1
        value = valuegetter.getitem(fmtiter.fmt[i0:ik])
        gotvalue = True
        c = fmtiter.next()
    c, flags = peel_flags(c, fmtiter)
    c, width = peel_num(space, c, fmtiter, valuegetter)
    if c == '.':
        c, prec = peel_num(space, fmtiter.next(), fmtiter, valuegetter)
        flags.prec = True
    else:
        prec = 0
        flags.prec = False
    if c in 'hlL':
        c = fmtiter.next()
    if width < 0:
        # this can happen with *-args
        flags.f_ljust = True
        width = -width
    if not gotvalue:
        if c == '%':
            # did YOU realize that "%4%"%() == '   %'??
            value = valuegetter.makevalue('%')
            c = 's'
        else:
            value = valuegetter.nextvalue()
    return (c, flags, width, prec, value)


class NeedUnicodeFormattingError(Exception):
    pass

def numeric_preprocess(v, flags):
    # negative zeroes?
    # * mwh giggles, falls over
    # still, if we can recognize them, here's the place to do it.
    import math
    if v < 0 or v == 0 and isinstance(v, float) and math.atan2(0, v) != 0:
        sign = '-'
        v = -v
    else:
        if flags.f_sign:
            sign = '+'
        elif flags.f_blank:
            sign = ' '
        else:
            sign = ''
    return v, sign
numeric_preprocess._annspecialcase_ = 'specialize:argtype(0)'

def numeric_postprocess(r, sign, char, flags, width, prefix=""):
    assert char in 'iduoxXeEfFgG'
    padchar = ' '
    if flags.f_zero:
        padchar = '0'
    p = width - len(r) - len(sign) - len(prefix)
    if p < 0:
        p = 0
    if flags.f_ljust:
        r = sign + prefix + r + ' '*p
    else:
        if flags.f_zero:
            r = sign+prefix+padchar*p + r
        else:
            r = padchar*p + sign + prefix + r
    return r

def std_wp(r, char, flags, width, prec):
    assert char not in 'iduoxXeEfFgG'
    if flags.prec:
        if prec > 0:
            r = r[:prec]
        else:
            x = len(r) + prec
            assert x >= 0
            r = r[:x]
    p = width - len(r)
    if p < 0:
        p = 0
    if flags.f_ljust:
        r = r + ' '*p
    else:
        r = ' '*p + r
    return r

def std_wp_unicode(r, char, flags, width, prec):
    assert char not in 'iduoxXeEfFgG'
    if flags.prec:
        if prec > 0:
            r = r[:prec]
        else:
            x = len(r) + prec
            assert x >= 0
            r = r[:x]
    p = width - len(r)
    if p < 0:
        p = 0
    if flags.f_ljust:
        r = r + [unichr(ord(' '))]*p
    else:
        r = [unichr(ord(' '))]*p + r
    return r

def repr_format(space, char, flags, width, prec, valuebox):
    return std_wp(valuebox.repr(), char, flags, width, prec)

def percent_format(space, char, flags, width, prec, valuebox):
    return std_wp('%', char, flags, width, prec)

# isinf isn't too hard...
def isinf(v):
    return v != 0 and v*2.0 == v

# To get isnan, working x-platform and both on 2.3 and 2.4, is a
# horror.  I think this works (for reasons I don't really want to talk
# about), and probably when implemented on top of pypy, too.
def isnan(v):
    return v != v*1.0 or (v == 1.0 and v == 2.0)

def float_formatd(space, kind, v, flags, prec):
    try:
        return rarithmetic.formatd_overflow(flags.f_alt, prec, kind, v)
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap("formatted float is too long (precision too large?)"))

def float_f_format(space, char, flags, width, prec, valuebox):
    v = valuebox.maybe_float()
    if isnan(v):
        return 'nan'
    elif isinf(v):
        return 'inf'
    if not flags.prec:
        prec = 6
    v, sign = numeric_preprocess(v, flags)
    if v/1e25 > 1e25:
        return float_g_format(space, 'g', flags, width, prec, valuebox)
    return numeric_postprocess(float_formatd(space, 'f', v, flags, prec),
                               sign, char, flags, width)

def float_e_format(space, char, flags, width, prec, valuebox):
    v = valuebox.maybe_float()
    if isnan(v):
        return 'nan'
    elif isinf(v):
        return 'inf'    
    if not flags.prec:
        prec = 6
    v, sign = numeric_preprocess(v, flags)
    return numeric_postprocess(float_formatd(space, 'e', v, flags, prec),
                               sign, char, flags, width)

def float_g_format(space, char, flags, width, prec, valuebox):
    # The description of %g in the Python documentation lies
    # in a variety of minor ways.
    # Gah, this still isn't quite right in the f_alt case.
    # (One has to wonder who might care).
    v = valuebox.maybe_float()
    if isnan(v):
        return 'nan'
    elif isinf(v):
        return 'inf'    
    if not flags.prec:
        prec = 6
    v, sign = numeric_preprocess(v, flags)
    return numeric_postprocess(float_formatd(space, 'g', v, flags, prec),
                               sign, char, flags, width)

def format_num_helper_generator(fun_name, fun):
    def format_num_helper(space, valuebox, flags):
        v = valuebox.maybe_int()
        try:
            value = space.int_w(v)
            value, sign = numeric_preprocess(value, flags)
            return (fun(value), sign)
        except OperationError, operr:
            # XXX: Fix it, this is obviously inefficient
            if not operr.match(space, space.w_OverflowError):
                raise
            if space.is_true(space.lt(v, space.wrap(0))):
                sign = '-'
                v = space.neg(v)
            else:
                if flags.f_sign:
                    sign = '+'
                elif flags.f_blank:
                    sign = ' '
                else:
                    sign = ''
            val = space.str_w(getattr(space, fun_name)(v))
            return (val, sign)
    format_num_helper.func_name = fun_name + '_num_helper'
    return format_num_helper

hex_num_helper = format_num_helper_generator('hex', hex)
oct_num_helper = format_num_helper_generator('oct', oct)
int_num_helper = format_num_helper_generator('str', str)

def hex_format(space, char, flags, width, prec, valuebox):
    # NB: this has 2.4 semantics wrt. negative values
    r, sign = hex_num_helper(space, valuebox, flags)
    r = r[2:]
    if r[-1] == "L":
        # workaround weird behavior of CPython's hex
        r = r[:-1].lower()
    if flags.prec and len(r) < prec:
        
        r = '0'*(prec - len(r)) + r
    if flags.f_alt:
        prefix = '0x'
    else:
        prefix = ''
    if char == 'X':
        r = r.upper()
        prefix = prefix.upper()
    return numeric_postprocess(r, sign, char, flags, width, prefix)

def oct_format(space, char, flags, width, prec, valuebox):
    r, sign = oct_num_helper(space, valuebox, flags)
    if r[-1] == "L":
        r = r[:-1]
    if space.is_true(valuebox.maybe_int()) and not flags.f_alt:
        r = r[1:]
    if flags.prec and len(r) < prec:
        r = '0'*(prec - len(r)) + r
    return numeric_postprocess(r, sign, char, flags, width)

def int_format(space, char, flags, width, prec, valuebox):
    r, sign = int_num_helper(space, valuebox, flags)
    # XXX arbitrary overflow
    if prec > 1000:
        raise OperationError(space.w_OverflowError, space.wrap
                             ("Precision (%d) too large" % prec))
    if width > 1000:
        raise OperationError(space.w_OverflowError, space.wrap
                             ("Width (%d) too large" % width))
    if flags.prec and len(r) < prec:
        r = '0'*(prec - len(r)) + r
    return numeric_postprocess(r, sign, char, flags, width)

def char_format(space, char, flags, width, prec, valuebox):
    if valuebox.isstr():
        v = valuebox.str()
        if len(v) != 1:
            raise OperationError(space.w_TypeError, space.wrap("%c requires int or char"))
    elif valuebox.isunicode():
        raise NeedUnicodeFormattingError
    else:
        i = space.int_w(valuebox.maybe_int())
        if not 0 <= i <= 255:
            raise OperationError(space.w_OverflowError,
                                 space.wrap("OverflowError: unsigned byte "
                                "integer is greater than maximum"))
        v = chr(i)
    flags.prec = False
    return std_wp(v, char, flags, width, 0)

def string_format(space, char, flags, width, prec, valuebox):
    if valuebox.isunicode():
        raise NeedUnicodeFormattingError
    return std_wp(valuebox.str(), char, flags, width, prec)

str_format_registry = {
    'd':int_format,
    'i':int_format,
    'o':oct_format,
    'u':int_format,
    'x':hex_format,
    'X':hex_format,
    'e':float_e_format,
    'E':float_e_format,
    'f':float_f_format,
    'F':float_f_format,
    'g':float_g_format,
    'G':float_g_format,
    'c':char_format,
    's':string_format,
    'r':repr_format, 
    # this *can* get accessed, by e.g. '%()4%'%{'':1}.
    # The usual %% case has to be handled specially as it
    # doesn't consume a value.
    '%':percent_format, 
    }

def unicode_string_format(space, char, flags, width, prec, valuebox):
    return std_wp_unicode(valuebox.unicode(), char, flags, width, prec)

def unicode_char_format(space, char, flags, width, prec, valuebox):
    if valuebox.isunicode():
        v = valuebox.unicode()
        if len(v) != 1:
            raise TypeError, "%c requires int or unicode char"
    elif valuebox.isstr():
        v = space.unichars_w(space.wrap(valuebox.str()))
        if len(v) != 1:
            raise TypeError, "%c requires int or unicode char"
    else:
        i = space.int_w(valuebox.maybe_int())
        if not 0 <= i <= sys.maxunicode:
            raise OverflowError("OverflowError: unsigned byte "
                                "integer is greater than maximum")
        v = [unichr(i)]
    flags.prec = False
    return std_wp_unicode(v, char, flags, width, 0)

class FmtIter(object):
    def __init__(self, fmt):
        self.fmt = fmt
        self._fmtlength = len(fmt)
        self.i = 0

    def __iter__(self):
        return self

    def next(self):
        if self.i >= self._fmtlength:
            raise StopIteration
        c = self.fmt[self.i]
        self.i += 1
        return c

    def skip_to_fmt(self):
        i = self.i
        j = self.fmt.find('%', i)
        if j < 0:
            self.i = len(self.fmt)
            assert i > 0
            return self.fmt[i:]
        else:
            self.i = j
            assert i > 0
            assert j > 0
            return self.fmt[i:j]


def format(space, w_fmt, w_values, w_valuedict, do_unicode=False):
    vb = ValueGetter(space, w_values, w_valuedict)
    if not do_unicode:
        return _format(space, space.str_w(w_fmt), vb)
    else:
        fmt = space.str_w(w_fmt)
        fmtiter = FmtIter(fmt)
        return _format_unicode(space, fmtiter, vb, [], [])

def parse_and_check_fmt(space, fmtiter, valuegetter):
    try:
        t = parse_fmt(space, fmtiter, valuegetter)
    except StopIteration:
        raise OperationError(space.w_ValueError,
                             space.wrap("incomplete format"))
    try:
        f = str_format_registry[t[0]]
    except KeyError:
        char = t[0]
        if isinstance(char, unicode):
            char = char.encode(sys.getdefaultencoding(), 'replace')
        raise OperationError(space.w_ValueError,
                             space.wrap("unsupported format character "
                                        "'%s' (0x%x) at index %d"
                                        % (char, ord(t[0]), fmtiter.i - 1)))
    return t, f

def _format(space, fmt, valuegetter):
    fmtiter = FmtIter(fmt)
    r = []
    # iterator done by hand
    while 1:
        try:
            c = fmtiter.next()
            if c == '%':
                t = parse_and_check_fmt(space, fmtiter, valuegetter)
                (char, flags, width, prec, value), f = t
                try:
                    result = f(space, char, flags, width, prec, value)
                except NeedUnicodeFormattingError:
                    f_list = check_unicode_registry(space, t)
                    return _format_unicode(space, fmtiter, valuegetter, r, f_list)
                else:
                    r.append(result)
            else:
                # efficiency hack:
                r.append(c + fmtiter.skip_to_fmt())
        except StopIteration:
            break
    valuegetter.check_consumed()
    return space.wrap(''.join(r))

def check_unicode_registry(space, t):
    # XXX weird specialcasing, because functions returns different
    # stuff, need to fix unicode support in RPython for that
    (char, flags, width, prec, value), f = t    
    if char == 's':
        return unicode_string_format(space, char, flags, width, prec, value)
    elif char == 'c':
        return unicode_char_format(space, char, flags, width, prec, value)
    else:
        result = f(space, char, flags, width, prec, value)
        return space.unichars_w(space.wrap(result))

def _format_unicode(space, fmtiter, valuegetter, base_list=[], formatted_list=[]):
    r = []
    for i in base_list:
        r += space.unichars_w(space.wrap(i))
    r += formatted_list
    # iterator done by hand
    while 1:
        try:
            c = fmtiter.next()
            if c == '%':
                t = parse_and_check_fmt(space, fmtiter, valuegetter)
                r += check_unicode_registry(space, t)
            else:
                # efficiency hack:
                r += [unichr(ord(i)) for i in c + fmtiter.skip_to_fmt()]
        except StopIteration:
            break
    valuegetter.check_consumed()
    return space.newunicode(r)

class ValueGetter:
    """ statefull accesstor to Interpolation Values. """

    def __init__(self, space, w_values, w_valuedict):
        self.space = space
        self.values_w = space.unpacktuple(w_values)
        self.w_valuedict = w_valuedict
        self._valueindex = 0

    def check_consumed(self):
        space = self.space
        if (self._valueindex < len(self.values_w) and 
            space.is_w(self.w_valuedict, space.w_None)):
            raise OperationError(space.w_TypeError,
               space.wrap('not all arguments converted '
                            'during string formatting'))

    def makevalue(self, string):
        return ValueBox(self.space, self.space.wrap(string))

    def nextvalue(self):
        space = self.space
        if self._valueindex >= len(self.values_w):
            raise OperationError(space.w_TypeError, space.wrap(
                'not enough arguments for format string'))
        val = self.values_w[self._valueindex]
        self._valueindex += 1
        return ValueBox(space, val)

    def getitem(self, key):
        return ValueBox(self.space,
                        self.space.getitem(self.w_valuedict,
                                           self.space.wrap(key)))

class ValueBox:
    def __init__(self, space, w_value):
        self.space = space
        self.w_value = w_value
    
    def str(self):
        return self.space.str_w(self.space.str(self.w_value))
    
    def repr(self):
        return self.space.str_w(self.space.repr(self.w_value))

    def isint(self):
        space = self.space
        return space.is_true(space.isinstance(self.w_value, space.w_int))
    
    def isstr(self):
        space = self.space
        return space.is_true(space.isinstance(self.w_value, space.w_str))

    def isunicode(self):
        space = self.space
        return space.is_true(space.isinstance(self.w_value, space.w_unicode))

    def maybe_int(self):
        space = self.space
        if space.is_true(space.isinstance(self.w_value, space.w_int)):
            return self.w_value
        try:
            w_fun = space.getattr(self.w_value, space.wrap('__int__'))
        except OperationError, operr:
            if not operr.match(space, space.w_AttributeError):
                raise
            raise OperationError(space.w_TypeError,
                                 space.wrap("int argument required"))
        return space.call_function(w_fun)

    def maybe_float(self):
        space = self.space
        if space.is_true(space.isinstance(self.w_value, space.w_float)):
            return space.float_w(self.w_value)
        try:
            w_fun = space.getattr(self.w_value, space.wrap('__float__'))
        except OperationError, operr:
            if not operr.match(space, space.w_AttributeError):
                raise
            raise OperationError(space.w_TypeError,
                                 space.wrap("float argument required"))
        return space.float_w(space.call_function(w_fun))

    def __str__(self):
        raise ValueError("use self.str()")

    def unicode(self):
        space = self.space
        if space.is_true(space.isinstance(self.w_value, space.w_unicode)):
            return space.unichars_w(self.w_value)
        try:
            w_fun = space.getattr(self.w_value, space.wrap('__unicode__'))
        except OperationError, operr:
            if not operr.match(space, space.w_AttributeError):
                raise
            return space.unichars_w(space.str(self.w_value))
        return space.unichars_w(space.call_function(w_fun))
