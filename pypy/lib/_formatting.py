
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


import sys, py

class _Flags(object):
    def __repr__(self):
        return "<%s>"%(', '.join([f for f in self.__dict__
                                  if f[0] == 'f' and getattr(self, f)]),)
    f_ljust = 0
    f_sign = 0
    f_blank = 0
    f_alt = 0
    f_zero = 0


def peel_num(c, fmtiter, valuegetter):
    if c == '*':
        v = valuegetter.nextvalue()
        if not v.isint():
            raise TypeError, "* wants int"
        return fmtiter.next(), v.maybe_int()
    i0 = fmtiter.i - 1
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


def parse_fmt(fmtiter, valuegetter):
    """return (char, flags, width, prec, value)
    partially consumes fmtiter & valuegetter"""
    c = fmtiter.next()
    value = None
    gotvalue = False
    if c == '(':
        i0 = fmtiter.i
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
    c, width = peel_num(c, fmtiter, valuegetter)
    if c == '.':
        c, prec = peel_num(fmtiter.next(), fmtiter, valuegetter)
    else:
        prec = None
    if c in 'hlL':
        c = fmtiter.next()
    if width and width < 0:
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


#class Formatter(object):
#    def __init__(self, char, flags, width, prec, valuebox):
#        self.char = char
#        self.flags = flags
#        self.width = width
#        self.prec = prec
#        self.valuebox = valuebox

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

def numeric_postprocess(r, sign, char, flags, width, prefix=""):
    assert char in 'iduoxXeEfFgG'
    padchar = ' '
    if flags.f_zero:
        padchar = '0'
    if width is not None:
        p = width - len(r) - len(sign) -len(prefix)
        if flags.f_ljust:
            r = sign + prefix + r + ' '*p
        else:
            if flags.f_zero:
                r = sign+prefix+padchar*p + r
            else:
                r = padchar*p + sign + prefix + r
    else:
        r = sign + prefix + r
    return r

def std_wp(r, char, flags, width, prec):
    assert char not in 'iduoxXeEfFgG'
    if prec is not None:
        r = r[:prec]
    if width is not None:
        p = width - len(r)
        if flags.f_ljust:
            r = r + ' '*p
        else:
            r = ' '*p + r
    return r

def repr_format(char, flags, width, prec, valuebox):
    return std_wp(valuebox.repr(), char, flags, width, prec)

def percent_format(char, flags, width, prec, valuebox):
    return std_wp('%', char, flags, width, prec)

# isinf isn't too hard...
def isinf(v):
    return v != 0 and v*2.0 == v

# To get isnan, working x-platform and both on 2.3 and 2.4, is a
# horror.  I think this works (for reasons I don't really want to talk
# about), and probably when implemented on top of pypy, too.
def isnan(v):
    return v != v*1.0 or (v == 1.0 and v == 2.0)

#def eDigits(ds, flags, prec):
#    ds = ds[:prec + 1] + ['0'] * (prec + 1 - len(ds))
#    if prec > 0 or flags.f_alt:
#        ds[1:1] = ['.']
#    return ''.join(ds)

#def fDigits(ds, k, prec):
#    p = max(prec, 0)
#    if 0 < k < len(ds):
#        if len(ds) - k < p:
#            ds.extend(['0'] * (p - (len(ds) - k)))
#        else:
#            ds = ds[:p + k]
#        ds[k:k] = ['.']
#    elif k <= 0:
#        ds[0:0] = ['0']*(-k)
#        ds = ds[:p]
#        ds.extend(['0'] * (p - len(ds)))
#        ds[0:0]= ['0', '.']
#    elif k >= len(ds):
#        ds.extend((k-len(ds))*['0'] + ['.'] + ['0']*p)
#    return ''.join(ds)

def float_format(char, flags, valuebox):
    v = valuebox.maybe_float()
    if isnan(v):
        return 'nan'
    elif isinf(v):
        return 'inf'
    return numeric_preprocess(v, flags)

def float_formatd(kind, v, flags, prec):
    import __builtin__
    return __builtin__._formatd(flags.f_alt, prec, kind, v)

def float_f_format(char, flags, width, prec, valuebox):
    if prec is None:
        prec = 6
    v, sign = float_format(char, flags, valuebox)
    if v/1e25 > 1e25:
        return float_g_format('g', flags, width, prec, valuebox)
    return numeric_postprocess(float_formatd('f', v, flags, prec),
                               sign, char, flags, width)

def float_e_format(char, flags, width, prec, valuebox):
    if prec is None:
        prec = 6
    v, _ = float_format(char, flags, valuebox)
    return numeric_postprocess(float_formatd('e', v, flags, prec),
                               sign, char, flags, width)

def float_g_format(char, flags, width, prec, valuebox):
    # The description of %g in the Python documentation lies
    # in a variety of minor ways.
    # Gah, this still isn't quite right in the f_alt case.
    # (One has to wonder who might care).
    if prec is None:
        prec = 6
    v, sign = float_format(char, flags, valuebox)
    return numeric_postprocess(float_formatd('g', v, flags, prec),
                               sign, char, flags, width)

def hex_format(char, flags, width, prec, valuebox):
    # NB: this has 2.4 semantics wrt. negative values
    v, sign = numeric_preprocess(valuebox.maybe_int(), flags)
    r = hex(v)[2:]
    if r[-1]=="L":
        # workaround weird behavior of CPython's hex
        r = r[:-1].lower()
    if prec is not None and len(r) < prec:
        r = '0'*(prec - len(r)) + r
    if flags.f_alt:
        prefix = '0x'
    else:
        prefix = ''
    if char == 'X':
        r = r.upper()
        prefix = prefix.upper()
    return numeric_postprocess(r, sign, char, flags, width, prefix)

def oct_format(char, flags, width, prec, valuebox):
    v, sign = numeric_preprocess(valuebox.maybe_int(), flags)
    r = oct(v)
    if r[-1] == "L":
        r = r[:-1]
    if v and not flags.f_alt:
        r = r[1:]
    if prec is not None and len(r) < prec:
        r = '0'*(prec - len(r)) + r
    return numeric_postprocess(r, sign, char, flags, width)

def int_format(char, flags, width, prec, valuebox):
    v, sign = numeric_preprocess(valuebox.maybe_int(), flags)
    r = str(v)
    if prec is not None and len(r) < prec:
        r = '0'*(prec - len(r)) + r
    return numeric_postprocess(r, sign, char, flags, width)

def char_format(char, flags, width, prec, valuebox):
    if valuebox.isstr():
        v = valuebox.str()
        if len(v) != 1:
            raise TypeError, "%c requires int or char"
    elif valuebox.isunicode():
        raise NeedUnicodeFormattingError
    else:
        i = valuebox.maybe_int()
        if not 0 <= i <= 255:
            raise OverflowError("OverflowError: unsigned byte "
                                "integer is greater than maximum")
        v = chr(i)
    return std_wp(v, char, flags, width, None)

def string_format(char, flags, width, prec, valuebox):
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

def unicode_string_format(char, flags, width, prec, valuebox):
    return std_wp(valuebox.unicode(), char, flags, width, prec)

def unicode_char_format(char, flags, width, prec, valuebox):
    if valuebox.isunicode():
        v = valuebox.unicode()
        if len(v) != 1:
            raise TypeError, "%c requires int or unicode char"
    elif valuebox.isstr():
        v = unicode(valuebox.str())
        if len(v) != 1:
            raise TypeError, "%c requires int or unicode char"
    else:
        i = valuebox.maybe_int()
        if not 0 <= i <= sys.maxunicode:
            raise OverflowError("OverflowError: unsigned byte "
                                "integer is greater than maximum")
        v = unichr(i)
    return std_wp(v, char, flags, width, None)

unicode_format_registry = {
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
    'c':unicode_char_format,
    's':unicode_string_format,
    'r':repr_format, 
    # this *can* get accessed, by e.g. '%()4%'%{'':1}.
    # The usual %% case has to be handled specially as it
    # doesn't consume a value.
    '%':percent_format, 
    }
    

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
            return self.fmt[i:]
        else:
            self.i = j
            return self.fmt[i:j]


def format(fmt, values, valuedict=None, do_unicode=False):
    vb = ValueGetter(values, valuedict)
    return _format(fmt, vb, do_unicode)

def _format(fmt, valuegetter, do_unicode=False):
    if do_unicode:
        format_registry = unicode_format_registry
    else:
        format_registry = str_format_registry
    fmtiter = FmtIter(fmt)
    r = []
    for c in fmtiter: 
        if c == '%':
            try:
                t = parse_fmt(fmtiter, valuegetter)
            except StopIteration:
                raise ValueError, "incomplete format"
            try:
                f = format_registry[t[0]]
            except KeyError:
                char = t[0]
                if isinstance(char, unicode):
                    char = char.encode(sys.getdefaultencoding(), 'replace')
                raise ValueError("unsupported format character "
                                 "'%s' (0x%x) at index %d"
                                 % (char, ord(t[0]), fmtiter.i - 1))
            # Trying to translate this using the flow space.
            # Currently, star args give a problem there,
            # so let's be explicit about the args:
            # r.append(f(*t).format())
            char, flags, width, prec, value = t
            try:
                result = f(char, flags, width, prec, value)
            except NeedUnicodeFormattingError:
                # Switch to using the unicode formatters and retry.
                do_unicode = True
                format_registry = unicode_format_registry
                f = format_registry[t[0]]
                r.append(f(char, flags, width, prec, value))
            else:
                r.append(result)
        else:
            # efficiency hack:
            r.append(c + fmtiter.skip_to_fmt())
    valuegetter.check_consumed()
    if do_unicode:
        return u''.join(r)
    return ''.join(r)


class ValueGetter:
    """ statefull accesstor to Interpolation Values. """

    def __init__(self, values, valuedict):
        self._values = values
        self._valuedict = valuedict
        self._valueindex = 0

    def check_consumed(self):
        if (self._valueindex < len(self._values) and 
            self._valuedict is None):
            raise TypeError('not all arguments converted '
                            'during string formatting')

    def makevalue(self, string):
        return ValueBox(string)

    def nextvalue(self):
        if self._valueindex >= len(self._values):
            raise TypeError('not enough arguments for format string')
        val = self._values[self._valueindex]
        self._valueindex += 1
        return ValueBox(val)

    def getitem(self, key):
        return ValueBox(self._valuedict[key])

class ValueBox:
    def __init__(self, value):
        self._value = value
    def str(self):
        return str(self._value)
    def repr(self):
        return repr(self._value) 

    def isint(self):
        return isinstance(self._value, int)
    def isstr(self):
        return isinstance(self._value, str)
    def isunicode(self):
        return isinstance(self._value, unicode)

    def maybe_int(self):
        try:
            inter = self._value.__int__
        except AttributeError:
            raise TypeError, "int argument required"
        return inter()

    def maybe_float(self):
        try:
            floater = self._value.__float__
        except AttributeError:
            raise TypeError, "float argument required"
        return floater()

    def __str__(self):
        raise ValueError("use self.str()")

    def unicode(self):
        if self.isunicode():
            return self._value 
        if hasattr(self._value,'__unicode__'):
            return self._value.__unicode__()
        return unicode(self.str())
