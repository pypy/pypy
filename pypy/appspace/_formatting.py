class _Flags(object):
    def __repr__(self):
        return "<%s>"%(', '.join([f for f in self.__dict__ 
                                  if f[0] == 'f' and getattr(self, f)]),)
    f_ljust = 0
    f_sign = 0
    f_blank = 0
    f_alt = 0
    f_zero = 0

def value_next(valueiter):
    try:
        return valueiter.next()
    except StopIteration:
        raise TypeError('not enough arguments for format string')
    

def peel_num(c, fmtiter, valueiter):
    if c == '*':
        v = value_next(valueiter)
        if not isinstance(v, int):
            raise TypeError, "* wants int"
        return fmtiter.next(), v
    n = ''
    while c in '0123456789':
        n += c
        c = fmtiter.next()
    if n:
        return c, int(n)
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

def parse_fmt(fmtiter, valueiter, valuedict):
    """return (char, flags, width, prec, value)
    partially consumes fmtiter & valueiter"""
    c = fmtiter.next()
    gotvalue = False
    if c == '(':
        n = ''
        pcount = 1
        while 1:
            c = fmtiter.next()
            if c == ')':
                pcount -= 1
                if pcount == 0:
                    break
            elif c == '(':
                pcount += 1
            n += c
        value = valuedict[n]
        gotvalue = True
        c = fmtiter.next()
    c, flags = peel_flags(c, fmtiter)
    c, width = peel_num(c, fmtiter, valueiter)
    if c == '.':
        c, prec = peel_num(fmtiter.next(), fmtiter, valueiter)
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
            value = '%'
            c = 's'
        else:
            value = value_next(valueiter)
    return (c, flags, width, prec, value)

class Formatter(object):
    def __init__(self, char, flags, width, prec, value):
        self.char = char
        self.flags = flags
        self.width = width
        self.prec = prec
        self.value = value

    def format(self):
        raise NotImplementedError

    def std_wp(self, r):
        padchar = ' '
        if self.flags.f_zero and self.char in 'iduoxXeEfFgG':
            padchar = '0'
        
        if self.prec is not None:
            r = r[:self.prec]
        if self.width is not None:
            p = self.width - len(r)
            if self.flags.f_ljust:
                r = r + ' '*p
            else:
                r = padchar*p + r
        return r

def funcFormatter(*funcs):
    class _F(Formatter):
        def format(self):
            r = self.value
            for f in funcs:
                r = f(r)
            return self.std_wp(r)
    return _F

def maybe_int(value):
    try:
        inter = value.__int__
    except AttributeError:
        raise TypeError, "an integer argument is required"
    return inter()

class floatFFormatter(Formatter):
    def format(self):
        if self.prec is None:
            self.prec = 6
        r = str(int(self.value))
        # XXX this is a bit horrid
        if self.prec > 0:
            frac_part = str(self.value%1)[1:2+self.prec]
            if len(frac_part) < self.prec + 1:
               frac_part += (1 + self.prec - len(frac_part)) * '0' 
            r += frac_part
        self.prec = None
        return self.std_wp(r)

format_registry = {
    's':funcFormatter(str),
    'r':funcFormatter(repr),
    'x':funcFormatter(maybe_int, hex),    
    'X':funcFormatter(maybe_int, hex, lambda r:r.upper()),
    'd':funcFormatter(maybe_int, str),
    'f':floatFFormatter,
    'g':funcFormatter(str),
    }
    
class FmtIter(object):
    def __init__(self, fmt):
        self.fmt = fmt
        self.i = 0
    def __iter__(self):
        return self
    def next(self):
        try:
            c = self.fmt[self.i]
        except IndexError:
            raise StopIteration
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

def format(fmt, values, valuedict=None):
    fmtiter = FmtIter(fmt)
    valueiter = iter(values)
    r = []
    try:
        for c in fmtiter:
            if c == '%':
                t = parse_fmt(fmtiter, valueiter, valuedict)
                try:
                    f = format_registry[t[0]]
                except KeyError:
                    raise ValueError("unsupported format character "
                                     "'%s' (%x) at index %d"
                                     %(t[0], ord(t[0]), fmtiter.i))
                r.append(f(*t).format())
            else:
                # efficiency hack:
                r.append(c + fmtiter.skip_to_fmt())
    except StopIteration:
        raise ValueError, "incomplete format"
    try:
        valueiter.next()
    except StopIteration:
        pass
    else:
        raise TypeError('not all arguments converted '
                        'during string formatting')
    return ''.join(r)
            
