import re
import math
import types
import warnings


PREC_REPR = 0 # 17
PREC_STR = 0 # 12


class complex(object):
    """complex(real[, imag]) -> complex number

    Create a complex number from a real part and an optional imaginary part.
    This is equivalent to (real + imag*1j) where imag defaults to 0."""
    
    def __init__(self, real=0.0, imag=None):
        if type(real) == types.StringType and imag is not None:
            msg = "complex() can't take second arg if first is a string"
            raise TypeError, msg

        if type(imag) == types.StringType:
            msg = "complex() second arg can't be a string"
            raise TypeError, msg

        if type(real) in types.StringTypes:
            real, imag = self._makeComplexFromString(real)
            self.__dict__['real'] = real
            self.__dict__['imag'] = imag
        else:
            if imag is None:
               imag = 0.
            self.__dict__['real'] = float(real)
            self.__dict__['imag'] = float(imag)
        

    def __setattr__(self, name, value):
        if name in ('real', 'imag'):
            raise TypeError, "readonly attribute"
        else:
            self.__dict__[name] = value


    def _makeComplexFromString(self, string):
        pat = re.compile(" *([\+\-]?\d*\.?\d*)([\+\-]?\d*\.?\d*)[jJ] *")
        m = pat.match(string)
        x, y = m.groups()
        if len(y) == 1 and y in '+-':
            y = y + '1.0'
        x, y = map(float, [x, y])
        return x, y


    def __description(self, precision):
        sign = '+'
        if self.imag < 0.:
            sign = ''
        if self.real != 0.:
            format = "(%%%02dg%%s%%%02dgj)" % (precision, precision)
            args = (self.real, sign, self.imag)
        else:
            format = "%%%02dgj" % precision
            args = self.imag
        return format % args


    def __repr__(self):
        return self.__description(PREC_REPR)


    def __str__(self):
        return self.__description(PREC_STR)

        
    def __hash__(self):
        hashreal = hash(self.real)
        hashimag = hash(self.imag)

        # Note:  if the imaginary part is 0, hashimag is 0 now,
        # so the following returns hashreal unchanged.  This is
        # important because numbers of different types that
        # compare equal must have the same hash value, so that
        # hash(x + 0*j) must equal hash(x).

        combined = hashreal + 1000003 * hashimag
        if combined == -1:
            combined = -2

        return combined


    def __add__(self, other):
        self, other = self.__coerce__(other)
        real = self.real + other.real
        imag = self.imag + other.imag
        return complex(real, imag)


    def __sub__(self, other):
        self, other = self.__coerce__(other)
        real = self.real - other.real
        imag = self.imag - other.imag
        return complex(real, imag)


    def __mul__(self, other):
        if other.__class__ != complex:
            return complex(other*self.real, other*self.imag)

        real = self.real*other.real - self.imag*other.imag
        imag = self.real*other.imag + self.imag*other.real
        return complex(real, imag)


    def __div__(self, other):
        if other.__class__ != complex:
            return complex(self.real/other, self.imag/other)

        if other.real < 0:
            abs_breal = -other.real
        else: 
            abs_breal = other.real
      
        if other.imag < 0:
            abs_bimag = -other.imag
        else:
            abs_bimag = other.imag

        if abs_breal >= abs_bimag:
            # divide tops and bottom by other.real
            if abs_breal == 0.0:
                real = imag = 0.0
            else:
                ratio = other.imag / other.real
                denom = other.real + other.imag * ratio
                real = (self.real + self.imag * ratio) / denom
                imag = (self.imag - self.real * ratio) / denom
        else:
            # divide tops and bottom by other.imag
            ratio = other.real / other.imag
            denom = other.real * ratio + other.imag
            assert other.imag != 0.0
            real = (self.real * ratio + self.imag) / denom
            imag = (self.imag * ratio - self.real) / denom

        return complex(real, imag)


    def __floordiv__(self, other):
        return self / other
        
        
    def __truediv__(self, other):
        return self / other
        

    def __mod__(self, other):
        warnings.warn("complex divmod(), // and % are deprecated", DeprecationWarning)

        if other.real == 0. and other.imag == 0.:
            raise ZeroDivisionError, "complex remainder"

        div = self/other # The raw divisor value.
        div = complex(math.floor(div.real), 0.0)
        mod = self - div*other

        if mod.__class__ == complex:
            return mod
        else:
            return complex(mod)


    def __divmod__(self, other):
        warnings.warn("complex divmod(), // and % are deprecated", DeprecationWarning)

        if other.real == 0. and other.imag == 0.:
            raise ZeroDivisionError, "complex remainder"

        div = self/other # The raw divisor value.
        div = complex(math.floor(div.real), 0.0)
        mod = self - div*other
        return div, mod


    def __pow__(self, other):
        if other.__class__ != complex:
            other = complex(other, 0)
                    
        a, b = self, other

        if b.real == 0. and b.imag == 0.:
            real = 1.
            imag = 0.
        elif a.real == 0. and a.imag == 0.:
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

        return complex(real, imag)


    def __neg__(self):
        return complex(-self.real, -self.imag)


    def __pos__(self):
        return complex(self.real, self.imag)


    def __abs__(self):
        result = math.hypot(self.real, self.imag)
        return float(result)


    def __nonzero__(self):
        return self.real != 0.0 or self.imag != 0.0


    def __coerce__(self, other):
        typ = type(other)
        
        if typ is types.IntType:
            return self, complex(float(other))
        elif typ is types.LongType:
            return self, complex(float(other))
        elif typ is types.FloatType:
            return self, complex(other)
        elif other.__class__ == complex:
            return self, other
        elif typ is types.ComplexType: # cough
            return self, complex(other.real, other.imag)
            
        raise TypeError, "number coercion failed"


    def conjugate(self):
        return complex(self.real, -self.imag)


    def __eq__(self, other):
        self, other = self.__coerce__(other)
        return self.real == other.real and self.imag == other.imag

    def __ne__(self, other):
        self, other = self.__coerce__(other)
        return self.real != other.real or self.imag != other.imag


    # unsupported operations
    
    def __lt__(self, other):
        raise TypeError, "cannot compare complex numbers using <, <=, >, >="

        
    def __le__(self, other):
        raise TypeError, "cannot compare complex numbers using <, <=, >, >="

        
    def __gt__(self, other):
        raise TypeError, "cannot compare complex numbers using <, <=, >, >="

        
    def __ge__(self, other):
        raise TypeError, "cannot compare complex numbers using <, <=, >, >="


    def __int__(self):
        raise TypeError, "can't convert complex to int; use e.g. int(abs(z))"


    def __long__(self):
        raise TypeError, "can't convert complex to long; use e.g. long(abs(z))"


    def __float__(self):
        raise TypeError, "can't convert complex to float; use e.g. float(abs(z))"


    def _unsupportedOp(self, other, op):
        selfTypeName = type(self).__name__
        otherTypeName = type(other).__name__
        args = (op, selfTypeName, otherTypeName)
        msg = "unsupported operand type(s) for %s: '%s' and '%s'" % args
        raise TypeError, msg


    def __and__(self, other):
        self._unsupportedOp(self, other, "&")


    def __or__(self, other):
        self._unsupportedOp(self, other, "|")


    def __xor__(self, other):
        self._unsupportedOp(self, other, "^")


    def __rshift__(self, other):
        self._unsupportedOp(self, other, ">>")


    def __lshift__(self, other):
        self._unsupportedOp(self, other, "<<")


    def __iand__(self, other):
        self._unsupportedOp(self, other, "&=")


    def __ior__(self, other):
        self._unsupportedOp(self, other, "|=")


    def __ixor__(self, other):
        self._unsupportedOp(self, other, "^=")


    def __irshift__(self, other):
        self._unsupportedOp(self, other, ">>=")


    def __ilshift__(self, other):
        self._unsupportedOp(self, other, "<<=")


    # augmented assignment operations
    
    def __iadd__(self, other):
        return self + other
    

    def __isub__(self, other):
        return self - other
    

    def __imul__(self, other):
        return self * other
    

    def __idiv__(self, other):
        return self / other
    

#    def __new__(self, ...):
#        pass


# test mod, divmod

# add radd, rsub, rmul, rdiv...

