
import math 
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped

class State: 
    def __init__(self, space): 
        self.w_e = space.wrap(math.e)
        self.w_pi = space.wrap(math.pi)
def get(space): 
    return space.fromcache(State) 

def pow(space, x, y): 
    """pow(x,y)
       
       Return x**y (x to the power of y).
    """
    return space.wrap(math.pow(x, y))
pow.unwrap_spec = [ObjSpace, float, float]

def cosh(space, x): 
    """cosh(x)
       
       Return the hyperbolic cosine of x.
    """
    return space.wrap(math.cosh(x))
cosh.unwrap_spec = [ObjSpace, float]

def ldexp(space, x,  i): 
    """ldexp(x, i) -> x * (2**i)
    """
    return space.wrap(math.ldexp(x,  i))
ldexp.unwrap_spec = [ObjSpace, float, int]

def hypot(space, x, y): 
    """hypot(x,y)
       
       Return the Euclidean distance, sqrt(x*x + y*y).
    """
    return space.wrap(math.hypot(x, y))
hypot.unwrap_spec = [ObjSpace, float, float]

def tan(space, x): 
    """tan(x)
       
       Return the tangent of x (measured in radians).
    """
    return space.wrap(math.tan(x))
tan.unwrap_spec = [ObjSpace, float]

def asin(space, x): 
    """asin(x)
       
       Return the arc sine (measured in radians) of x.
    """
    return space.wrap(math.asin(x))
asin.unwrap_spec = [ObjSpace, float]

def log(space, x,  w_base=NoneNotWrapped):
    """log(x[, base]) -> the logarithm of x to the given base.
       If the base not specified, returns the natural logarithm (base e) of x.
    """
    if w_base is None:
        return space.wrap(math.log(x))
    else:
        return space.wrap(math.log(x) / math.log(space.float_w(w_base)))
log.unwrap_spec = [ObjSpace, float, W_Root]

def fabs(space, x): 
    """fabs(x)
       
       Return the absolute value of the float x.
    """
    return space.wrap(math.fabs(x))
fabs.unwrap_spec = [ObjSpace, float]

def floor(space, x): 
    """floor(x)
       
       Return the floor of x as a float.
       This is the largest integral value <= x.
    """
    return space.wrap(math.floor(x))
floor.unwrap_spec = [ObjSpace, float]

def sqrt(space, x): 
    """sqrt(x)
       
       Return the square root of x.
    """
    return space.wrap(math.sqrt(x))
sqrt.unwrap_spec = [ObjSpace, float]

def frexp(space, x): 
    """frexp(x)
       
       Return the mantissa and exponent of x, as pair (m, e).
       m is a float and e is an int, such that x = m * 2.**e.
       If x is 0, m and e are both 0.  Else 0.5 <= abs(m) < 1.0.
    """
    mant, expo = math.frexp(x)
    return space.newtuple([space.wrap(mant), space.wrap(expo)])
frexp.unwrap_spec = [ObjSpace, float]

def degrees(space, x): 
    """degrees(x) -> converts angle x from radians to degrees
    """
    return space.wrap(math.degrees(x))
degrees.unwrap_spec = [ObjSpace, float]

def log10(space, x): 
    """log10(x) -> the base 10 logarithm of x.
    """
    return space.wrap(math.log10(x))
log10.unwrap_spec = [ObjSpace, float]

def fmod(space, x, y): 
    """fmod(x,y)
       
       Return fmod(x, y), according to platform C.  x % y may differ.
    """
    return space.wrap(math.fmod(x, y))
fmod.unwrap_spec = [ObjSpace, float, float]

def atan(space, x): 
    """atan(x)
       
       Return the arc tangent (measured in radians) of x.
    """
    return space.wrap(math.atan(x))
atan.unwrap_spec = [ObjSpace, float]

def ceil(space, x): 
    """ceil(x)
       
       Return the ceiling of x as a float.
       This is the smallest integral value >= x.
    """
    return space.wrap(math.ceil(x))
ceil.unwrap_spec = [ObjSpace, float]

def sinh(space, x): 
    """sinh(x)
       
       Return the hyperbolic sine of x.
    """
    return space.wrap(math.sinh(x))
sinh.unwrap_spec = [ObjSpace, float]

def cos(space, x): 
    """cos(x)
       
       Return the cosine of x (measured in radians).
    """
    return space.wrap(math.cos(x))
cos.unwrap_spec = [ObjSpace, float]

def tanh(space, x): 
    """tanh(x)
       
       Return the hyperbolic tangent of x.
    """
    return space.wrap(math.tanh(x))
tanh.unwrap_spec = [ObjSpace, float]

def radians(space, x): 
    """radians(x) -> converts angle x from degrees to radians
    """
    return space.wrap(math.radians(x))
radians.unwrap_spec = [ObjSpace, float]

def sin(space, x): 
    """sin(x)
       
       Return the sine of x (measured in radians).
    """
    return space.wrap(math.sin(x))
sin.unwrap_spec = [ObjSpace, float]

def atan2(space, y,  x): 
    """atan2(y, x)
       
       Return the arc tangent (measured in radians) of y/x.
       Unlike atan(y/x), the signs of both x and y are considered.
    """
    return space.wrap(math.atan2(y,  x))
atan2.unwrap_spec = [ObjSpace, float, float]

def modf(space, x): 
    """modf(x)
       
       Return the fractional and integer parts of x.  Both results carry the sign
       of x.  The integer part is returned as a real.
    """
    frac, intpart = math.modf(x)
    return space.newtuple([space.wrap(frac), space.wrap(intpart)])
modf.unwrap_spec = [ObjSpace, float]

def exp(space, x): 
    """exp(x)
       
       Return e raised to the power of x.
    """
    return space.wrap(math.exp(x))
exp.unwrap_spec = [ObjSpace, float]

def acos(space, x): 
    """acos(x)
       
       Return the arc cosine (measured in radians) of x.
    """
    return space.wrap(math.acos(x))
acos.unwrap_spec = [ObjSpace, float]
