# NOT_RPYTHON yet
"""
Plain Python definition of the 'complex' type.
"""


#XXX Hack: This float is supposed to overflow to inf
OVERFLOWED_FLOAT = float("1e10000000000000000000000000000000")

class complex(object):
    """complex(real[, imag]) -> complex number

    Create a complex number from a real part and an optional imaginary part.
    This is equivalent to (real + imag*1j) where imag defaults to 0."""
    PREC_REPR = 17
    PREC_STR = 12

    __slots__ = ['real', 'imag']

    # XXX this class is not well tested

    # provide __new__to prevent the default which has no parameters
    def __new__(typ, real=0.0, imag=None):
        if real.__class__ == complex and imag is None and typ is complex:
            return real
        ret = object.__new__(typ)
        ret._init(real, imag)
        return ret

    def __getnewargs__(self):
        return (complex(self.real, self.imag),)
    
    def __reduce__(self):
        return (self.__class__, (self.real, self.imag),
                getattr(self, '__dict__', None))

    def _init(self, real=0.0, imag=None):
        if isinstance(real, (str, unicode)): 
            if imag is not None:
                msg = "complex() can't take second arg if first is a string"
                raise TypeError, msg
            re, im = self._makeComplexFromString(real)
        elif isinstance(real, complex):
            re = real.real
            im = real.imag
        else:
            if hasattr(real, "__complex__"):
                co = real.__complex__()
                if not isinstance(co, complex):
                    raise TypeError, "complex() argument must be a string or a number"
                re = co.real
                im = co.imag
            else:
                re = float(real)
                im = 0.0
        if isinstance(imag, (str, unicode)): 
            msg = "complex() second arg can't be a string"
            raise TypeError, msg
        elif isinstance(imag, complex):
            re -= imag.imag
            im += imag.real
        elif imag is not None:
            im += float(imag)
        real_slot.__set__(self, re)
        imag_slot.__set__(self, im)

    def _makeComplexFromString(self, string_):
        import re
        string_ = string_.strip().lower()
        pat = re.compile("([\+\-]?\d*\.?\d*)?([\+\-]?\d*\.?\d*j)?")
        m = pat.match(string_)
        x, y = m.groups()
        if x is None:
            x = ""
        if y is None:
            y = ""
        if len(string_) - (len(x) + len(y)) != 0:
            raise ValueError, "complex() arg is a malformed string"
        if x == "":
            if y == "":
                raise ValueError, "complex() arg is an empty string"
            if y[-1] != "j":
                raise ValueError, "complex() arg is a malformed string"
            assert y[-1] == "j"
            y = y[:-1]
            if len(y) <= 1:
                y += "1"
            f = float(y)
            if abs(f) == OVERFLOWED_FLOAT:
                raise ValueError, "float() out of range: %s" % y
            return 0, f
        if y == "":
            f = float(x)
            if abs(f) == OVERFLOWED_FLOAT:
                raise ValueError, "float() out of range: %s" % x
            return f, 0
        if y[-1] != "j":
            raise ValueError, "complex() arg is a malformed string"
        assert y[-1] == "j"
        y = y[:-1]
        if y == "":
            if x in "+-":
                x += "1.0"
            f = float(x)
            if abs(f) == OVERFLOWED_FLOAT:
                raise ValueError, "float() out of range: %s" % x
            return 0, f
        if y in "+-":
            y += "1.0"
        x = float(x)
        y = float(y)
        if abs(x) == OVERFLOWED_FLOAT:
            raise ValueError, "float() out of range: %s" % x
        if abs(y) == OVERFLOWED_FLOAT:
            raise ValueError, "float() out of range: %s" % y
        return x, y

    def __description(self, precision):
        if self.real != 0.:
            return "(%.*g%+.*gj)"%(precision, self.real, precision, self.imag)
        else:
            return "%.*gj"%(precision, self.imag)


    def __repr__(self):
        return self.__description(self.PREC_REPR)


    def __str__(self):
        return self.__description(self.PREC_STR)

        
    def __hash__(self):
        hashreal = hash(self.real)
        hashimag = hash(self.imag)

        # Note:  if the imaginary part is 0, hashimag is 0 now,
        # so the following returns hashreal unchanged.  This is
        # important because numbers of different types that
        # compare equal must have the same hash value, so that
        # hash(x + 0*j) must equal hash(x).

        return hashreal + 1000003 * hashimag


    def __add__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        real = self.real + other.real
        imag = self.imag + other.imag
        return complex(real, imag)

    __radd__ = __add__

    def __sub__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        real = self.real - other.real
        imag = self.imag - other.imag
        return complex(real, imag)
    
    def __rsub__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return other.__sub__(self)

    def __mul__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        real = self.real*other.real - self.imag*other.imag
        imag = self.real*other.imag + self.imag*other.real
        return complex(real, imag)

    __rmul__ = __mul__

    def __div__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        if abs(other.real) >= abs(other.imag):
            # divide tops and bottom by other.real
            try:
                ratio = other.imag / other.real
            except ZeroDivisionError:
                raise ZeroDivisionError, "complex division"
            denom = other.real + other.imag * ratio
            real = (self.real + self.imag * ratio) / denom
            imag = (self.imag - self.real * ratio) / denom
        else:
            # divide tops and bottom by other.imag
            assert other.imag != 0.0
            ratio = other.real / other.imag
            denom = other.real * ratio + other.imag
            real = (self.real * ratio + self.imag) / denom
            imag = (self.imag * ratio - self.real) / denom

        return complex(real, imag)

    def __rdiv__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return other.__div__(self)

    def __floordiv__(self, other):
        result = self.__divmod__(other)
        if result is NotImplemented:
            return result
        div, mod = result
        return div

    def __rfloordiv__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return other.__floordiv__(self)

    __truediv__ = __div__
    __rtruediv__ = __rdiv__

    def __mod__(self, other):
        result = self.__divmod__(other)
        if result is NotImplemented:
            return result
        div, mod = result
        return mod

    def __rmod__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return other.__mod__(self)

    def __divmod__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result

        import warnings, math
        warnings.warn("complex divmod(), // and % are deprecated", DeprecationWarning)

        try:
            div = self/other # The raw divisor value.
        except ZeroDivisionError:
            raise ZeroDivisionError, "complex remainder"
        div = complex(math.floor(div.real), 0.0)
        mod = self - div*other
        return div, mod

    def __rdivmod__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return other.__divmod__(self)


    def __pow__(self, other, mod=None):
        if mod is not None:
            raise ValueError("complex modulo")
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        a, b = result
        import math

        if b.real == 0. and b.imag == 0.:
            real = 1.
            imag = 0.
        elif a.real == 0. and a.imag == 0.:
            if b.imag != 0. or b.real < 0.:
                raise ZeroDivisionError, "0.0 to a negative or complex power"
            real = 0.
            imag = 0.
        else:
            vabs = math.hypot(a.real,a.imag)
            len = math.pow(vabs,b.real)
            at = math.atan2(a.imag, a.real)
            phase = at*b.real
            if b.imag != 0.0:
                len /= math.exp(at*b.imag)
                phase += b.imag*math.log(vabs)
            real = len*math.cos(phase)
            imag = len*math.sin(phase)

        result = complex(real, imag)
        return result

    def __rpow__(self, other, mod=None):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return other.__pow__(self, mod)

    def __neg__(self):
        return complex(-self.real, -self.imag)


    def __pos__(self):
        return complex(self.real, self.imag)


    def __abs__(self):
        import math
        result = math.hypot(self.real, self.imag)
        return float(result)


    def __nonzero__(self):
        return self.real != 0.0 or self.imag != 0.0


    def __coerce__(self, other):
        if isinstance(other, complex):
            return self, other
        if isinstance(other, (int, long, float)):
            return self, complex(other)
        return NotImplemented

    def conjugate(self):
        return complex(self.real, -self.imag)

    def __eq__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return self.real == other.real and self.imag == other.imag

    def __ne__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        self, other = result
        return self.real != other.real or self.imag != other.imag


    # unsupported operations
    
    def __lt__(self, other):
        result = self.__coerce__(other)
        if result is NotImplemented:
            return result
        raise TypeError, "cannot compare complex numbers using <, <=, >, >="

    __le__ = __gt__ = __ge__ = __lt__


    def __int__(self):
        raise TypeError, "can't convert complex to int; use e.g. int(abs(z))"


    def __long__(self):
        raise TypeError, "can't convert complex to long; use e.g. long(abs(z))"


    def __float__(self):
        raise TypeError, "can't convert complex to float; use e.g. float(abs(z))"


real_slot = complex.real
imag_slot = complex.imag

# make the slots read-only
complex.real = property(real_slot.__get__)
complex.imag = property(imag_slot.__get__)
