# Application level implementation of string formatting.

# There's some insane stuff in here.  Blame CPython.  Please.

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
 
    def numeric_preprocess(self, v):
        # negative zeroes?
        # * mwh giggles, falls over
        # still, if we can recognize them, here's the place to do it.
        if v < 0:
            sign = '-'
            v = -v
        else:
            if self.flags.f_sign:
                sign = '+'
            elif self.flags.f_blank:
                sign = ' '
            else:
                sign = ''
        return v, sign

    def numeric_postprocess(self, r, sign):
        assert self.char in 'iduoxXeEfFgG'
        
        padchar = ' '
        if self.flags.f_zero:
            padchar = '0'
        
        if self.width is not None:
            p = self.width - len(r) - len(sign)
            if self.flags.f_ljust:
                r = sign + r + ' '*p
            else:
                if self.flags.f_zero:
                    r = sign+padchar*p + r
                else:
                    r = padchar*p + sign + r                    
        else:
            r = sign + r
        return r
        

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

def maybe_float(value):
    try:
        floater = value.__float__
    except AttributeError:
        raise TypeError, "float argument is required"
    return floater()

import math

# from the excessive effort department, routines for printing floating
# point numbers from

# "Printing Floating-Point Numbers Quickly and Accurately" by Burger &
# Dybvig, Proceedings of the SIGPLAN '96 Conference on Programming
# Language Design and Implementation.

# The paper contains scheme code which has been specialized for IEEE
# doubles and converted into (still somewhat scheme-like) Python by
# Michael Hudson.

# XXX unfortunately, we need the fixed-format output routines, the source
# for which is not included in the paper... for now, just put up with
# occasionally incorrectly rounded final digits.  I'll get to it.

# XXX should run this at interpreter level, really....

## (define flonum->digits
##   (lambda (v f e min-e p b B)
##     (if (>= e 0)
##         (if (not (= f (expt b (- p 1))))
##             (let ([be (expt b e)])
##               (scale (* f be 2) 2 be be 0 B v))
##             (let* ([be (expt b e)] [be1 (* be b)])
##                   (scale (* f be1 2) (* b 2) be1 be 0 B v)))
##         (if (or (= e min-e) (not (= f (expt b (- p 1)))))
##             (scale (* f 2) (* (expt b (- e)) 2) 1 1 0 B v)
##             (scale (* f b 2) (* (expt b (- 1 e)) 2) b 1 0 B v)))))

def flonum2digits(v, f, e, B):
    
    # sod generality in the extreme: we're working with ieee 754 64
    # bit doubles on any platform I care about.
    # this means b == 2, min-e = -1075 (?), p = 53 above

    # in:
    # v = f * 2**e
    # B is output base

    # out:
    # [d0, d1, ..., dn], k
    # st 0.[d1][d2]...[dn] * B**k is the "best" representation of v

    if e >= 0:
        if not f != 2**52:
            be = 2**e
            return scale(f*be*2, 2, be, be, 0, B, v)
        else:
            be = 2**e
            be1 = 2*be
            return scale(f*be1*2, 4, be1, be, 0, B, v)
    else:
        if e == -1075 or f != 2**52:
            return scale(f*2, 2*2**(-e), 1, 1, 0, B, v)
        else:
            return scale(f*4, 2*2**(1-e), 2, 1, 0, B, v)

## (define generate
##   (lambda (r s m+ m- B low-ok? high-ok?)
##     (let ([q-r (quotient-remainder (* r B) s)]
##           [m+ (* m+ B)]
##           [m- (* m- B)])
##       (let ([d (car q-r)]
##             [r (cdr q-r)])
##         (let ([tc1 ((if low-ok? <= <) r m-)]
##               [tc2 ((if high-ok? >= >) (+ r m+) s)])
##           (if (not tc1)
##               (if (not tc2)
##                   (cons d (generate r s m+ m- B low-ok? high-ok?))
##                   (list (+ d 1)))
##               (if (not tc2)
##                   (list d)
##                   (if (< (* r 2) s)
##                       (list d)
##                       (list (+ d 1))))))))))

# now the above is an example of a pointlessly recursive algorithm if
# ever i saw one...

def generate(r, s, m_plus, m_minus, B):
    rr = []
    while 1:
        d, r = divmod(r*B, s)
        m_plus *= B
        m_minus *= B
        tc1 = r < m_minus
        tc2 = (r + m_plus) > s
        if tc2:
            rr.append(d+1)
        else:
            rr.append(d)
        if tc1 or tc2:
            break
    return rr

## (define scale
##   (lambda (r s m+ m- k B low-ok? high-ok? v)
##     (let ([est (inexact->exact (ceiling (- (logB B v) 1e-10)))])
##       (if (>= est 0)
##           (fixup r (* s (exptt B est)) m+ m- est B low-ok? high-ok? )
##           (let ([scale (exptt B (- est))])
##             (fixup (* r scale) s (* m+ scale) (* m- scale) est B low-ok? high-ok? ))))))

def scale(r, s, m_plus, m_minus, k, B, v):
    est = long(math.ceil(math.log(v, B) - 1e-10))
    if est >= 0:
        return fixup(r, s * B ** est, m_plus, m_minus, est, B)
    else:
        scale = B ** -est
        return fixup(r*scale, s, m_plus*scale, m_minus*scale, est, B)

## (define fixup
##   (lambda (r s m+ m- k B low-ok? high-ok? )
##     (if ((if high-ok? >= >) (+ r m+) s) ; too low?
##         (cons (+ k 1) (generate r (* s B) m+ m- B low-ok? high-ok? ))
##         (cons k (generate r s m+ m- B low-ok? high-ok? )))))

def fixup(r, s, m_plus, m_minus, k, B):
    if r + m_plus > s:
        return generate(r, s*B, m_plus, m_minus, B), k + 1
    else:
        return generate(r, s, m_plus, m_minus, B), k
    

def float_digits(f):
    assert f >= 0
    if f == 0.0:
        return [], 1
    m, e = math.frexp(f)
    m = long(m*2.0**53)
    e -= 53
    ds, k = flonum2digits(f, m, e, 10)
    ds = map(str, ds)
    return ds, k

class floatFFormatter(Formatter):
    def format(self):
        v = maybe_float(self.value)
        if abs(v)/1e25 > 1e25:
            return floatGFormatter('g', self.flags, self.width,
                                   self.prec, self.value).format()
        v, sign = self.numeric_preprocess(v)

        if self.prec is None:
            self.prec = 6

        # we want self.prec digits after the radix point.

        # this is probably more complex than it needs to be:
        p = max(self.prec, 0)
        ds, k = float_digits(v)
        if 0 < k < len(ds):
            if len(ds) - k < p:
                ds.extend(['0'] * (p - (len(ds) - k)))
            else:
                ds = ds[:p + k]
            ds[k:k] = ['.']
        elif k <= 0:
            ds[0:0] = ['0']*(-k)
            ds = ds[:p]
            ds.extend(['0'] * (p - len(ds)))
            ds[0:0]= ['0', '.']
        elif k >= len(ds):
            ds.extend((k-len(ds))*['0'] + ['.'] + ['0']*p)

        if self.prec <= 0:
            del ds[-1]
        
        return self.numeric_postprocess(''.join(ds), sign)

class floatEFormatter(Formatter):
    def format(self):
        v = maybe_float(self.value)

        v, sign = self.numeric_preprocess(v)

        if self.prec is None:
            self.prec = 6

        ds, k = float_digits(v)
        ds = ds[:self.prec + 1] + ['0'] * (self.prec + 1 - len(ds))
        ds[1:1] = ['.']

        r = ''.join(ds) + self.char + "%+03d"%(k-1,)

        return self.numeric_postprocess(r, sign)

class floatGFormatter(Formatter):
    # the description of %g in the Python documentation lies.
    def format(self):
        v = maybe_float(self.value)

        v, sign = self.numeric_preprocess(v)

        if self.prec is None:
            self.prec = 6

        ds, k = float_digits(v)

        ds = ds[:self.prec] # XXX rounding!

        if -4 < k < self.prec:
            if 0 < k < len(ds):
                ds[k:k] = ['.']
            if k <= 0:
                ds[0:0] = ['0', '.'] + ['0']*(-k)
            elif k >= len(ds):
                ds.extend((k-len(ds))*['0'])
            r = ''.join(ds)
        else:
            ds[1:1] = ['.']
            r = ''.join(ds) + self.char + "%+03d"%(k-1,)
            
        return self.numeric_postprocess(r, sign)

class HexFormatter(Formatter):
    def format(self):
        i = maybe_int(self.value)
        r = hex(i)
        if not self.flags.f_alt:
            r = r[2:]
        if self.char == 'X':
            r = r.upper()
        return self.std_wp(r)

class OctFormatter(Formatter):
    def format(self):
        i = maybe_int(self.value)
        r = oct(i)
        if not self.flags.f_alt:
            r = r[1:]
        return self.std_wp(r)

format_registry = {
    's':funcFormatter(str),
    'r':funcFormatter(repr),
    'x':HexFormatter,
    'X':HexFormatter,
    'o':OctFormatter,
    'd':funcFormatter(maybe_int, str),
    'e':floatEFormatter,
    'E':floatEFormatter,
    'f':floatFFormatter,
    'g':floatGFormatter,
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
        if valuedict is None:
            raise TypeError('not all arguments converted '
                            'during string formatting')
    return ''.join(r)
            
