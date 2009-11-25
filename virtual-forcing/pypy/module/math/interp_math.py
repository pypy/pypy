
import math
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped

class State: 
    def __init__(self, space): 
        self.w_e = space.wrap(math.e)
        self.w_pi = space.wrap(math.pi)
def get(space): 
    return space.fromcache(State) 

def math1(space, f, x):
    try:
        y = f(x)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    return space.wrap(y)
math1._annspecialcase_ = 'specialize:arg(1)'

def math1_w(space, f, x):
    try:
        r = f(x)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    return r
math1_w._annspecialcase_ = 'specialize:arg(1)'

def math2(space, f, x, snd):
    try:
        r = f(x, snd)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    return space.wrap(r)
math2._annspecialcase_ = 'specialize:arg(1)'

def pow(space, x, y):
    """pow(x,y)
       
       Return x**y (x to the power of y).
    """
    return math2(space, math.pow, x, y)
pow.unwrap_spec = [ObjSpace, float, float]

def cosh(space, x): 
    """cosh(x)
       
       Return the hyperbolic cosine of x.
    """
    return math1(space, math.cosh, x)
cosh.unwrap_spec = [ObjSpace, float]

def ldexp(space, x,  i): 
    """ldexp(x, i) -> x * (2**i)
    """
    return math2(space, math.ldexp, x,  i)
ldexp.unwrap_spec = [ObjSpace, float, int]

def hypot(space, x, y): 
    """hypot(x,y)
       
       Return the Euclidean distance, sqrt(x*x + y*y).
    """
    return math2(space, math.hypot, x, y)
hypot.unwrap_spec = [ObjSpace, float, float]

def tan(space, x): 
    """tan(x)
       
       Return the tangent of x (measured in radians).
    """
    return math1(space, math.tan, x)
tan.unwrap_spec = [ObjSpace, float]

def asin(space, x): 
    """asin(x)
       
       Return the arc sine (measured in radians) of x.
    """
    return math1(space, math.asin, x)
asin.unwrap_spec = [ObjSpace, float]

def fabs(space, x): 
    """fabs(x)
       
       Return the absolute value of the float x.
    """
    return math1(space, math.fabs, x)
fabs.unwrap_spec = [ObjSpace, float]

def floor(space, x): 
    """floor(x)
       
       Return the floor of x as a float.
       This is the largest integral value <= x.
    """
    return math1(space, math.floor, x)
floor.unwrap_spec = [ObjSpace, float]

def sqrt(space, x): 
    """sqrt(x)
       
       Return the square root of x.
    """
    return math1(space, math.sqrt, x)
sqrt.unwrap_spec = [ObjSpace, float]

def frexp(space, x): 
    """frexp(x)
       
       Return the mantissa and exponent of x, as pair (m, e).
       m is a float and e is an int, such that x = m * 2.**e.
       If x is 0, m and e are both 0.  Else 0.5 <= abs(m) < 1.0.
    """
    mant, expo = math1_w(space, math.frexp, x)
    return space.newtuple([space.wrap(mant), space.wrap(expo)])
frexp.unwrap_spec = [ObjSpace, float]

degToRad = math.pi / 180.0

def degrees(space, x): 
    """degrees(x) -> converts angle x from radians to degrees
    """
    return space.wrap(x / degToRad)
degrees.unwrap_spec = [ObjSpace, float]

def _log_any(space, w_x, base):
    # base is supposed to be positive or 0.0, which means we use e
    try:
        if space.is_true(space.isinstance(w_x, space.w_long)):
            # special case to support log(extremely-large-long)
            num = space.bigint_w(w_x)
            result = num.log(base)
        else:
            x = space.float_w(w_x)
            if base == 10.0:
                result = math.log10(x)
            else:
                result = math.log(x) 
                if base != 0.0:
                    den = math.log(base)
                    result /= den
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap('math range error'))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap('math domain error'))
    return space.wrap(result)

def log(space, w_x, w_base=NoneNotWrapped):
    """log(x[, base]) -> the logarithm of x to the given base.
       If the base not specified, returns the natural logarithm (base e) of x.
    """
    if w_base is None:
        base = 0.0
    else:
        base = space.float_w(w_base)
        if base <= 0.0:
            # just for raising the proper errors
            return math1(space, math.log, base)
    return _log_any(space, w_x, base)
log.unwrap_spec = [ObjSpace, W_Root, W_Root]

def log10(space, w_x): 
    """log10(x) -> the base 10 logarithm of x.
    """ 
    return _log_any(space, w_x, 10.0)
log10.unwrap_spec = [ObjSpace, W_Root]

def fmod(space, x, y): 
    """fmod(x,y)
       
       Return fmod(x, y), according to platform C.  x % y may differ.
    """
    return math2(space, math.fmod, x, y)
fmod.unwrap_spec = [ObjSpace, float, float]

def atan(space, x): 
    """atan(x)
       
       Return the arc tangent (measured in radians) of x.
    """
    return math1(space, math.atan, x)
atan.unwrap_spec = [ObjSpace, float]

def ceil(space, x): 
    """ceil(x)
       
       Return the ceiling of x as a float.
       This is the smallest integral value >= x.
    """
    return math1(space, math.ceil, x)
ceil.unwrap_spec = [ObjSpace, float]

def sinh(space, x): 
    """sinh(x)
       
       Return the hyperbolic sine of x.
    """
    return math1(space, math.sinh, x)
sinh.unwrap_spec = [ObjSpace, float]

def cos(space, x): 
    """cos(x)
       
       Return the cosine of x (measured in radians).
    """
    return math1(space, math.cos, x)
cos.unwrap_spec = [ObjSpace, float]

def tanh(space, x): 
    """tanh(x)
       
       Return the hyperbolic tangent of x.
    """
    return math1(space, math.tanh, x)
tanh.unwrap_spec = [ObjSpace, float]

def radians(space, x): 
    """radians(x) -> converts angle x from degrees to radians
    """
    return space.wrap(x * degToRad)
radians.unwrap_spec = [ObjSpace, float]

def sin(space, x): 
    """sin(x)
       
       Return the sine of x (measured in radians).
    """
    return math1(space, math.sin, x)
sin.unwrap_spec = [ObjSpace, float]

def atan2(space, y,  x): 
    """atan2(y, x)
       
       Return the arc tangent (measured in radians) of y/x.
       Unlike atan(y/x), the signs of both x and y are considered.
    """
    return math2(space, math.atan2, y,  x)
atan2.unwrap_spec = [ObjSpace, float, float]

def modf(space, x): 
    """modf(x)
       
       Return the fractional and integer parts of x.  Both results carry the sign
       of x.  The integer part is returned as a real.
    """
    frac, intpart = math1_w(space, math.modf, x)
    return space.newtuple([space.wrap(frac), space.wrap(intpart)])
modf.unwrap_spec = [ObjSpace, float]

def exp(space, x): 
    """exp(x)
       
       Return e raised to the power of x.
    """
    return math1(space, math.exp, x)
exp.unwrap_spec = [ObjSpace, float]

def acos(space, x): 
    """acos(x)
       
       Return the arc cosine (measured in radians) of x.
    """
    return math1(space, math.acos, x)
acos.unwrap_spec = [ObjSpace, float]
