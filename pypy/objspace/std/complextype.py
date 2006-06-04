from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.objspace.std.strutil import interp_string_to_float, ParseStringError
from pypy.objspace.std.objspace import register_all
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.stdtypedef import GetSetProperty, StdTypeDef, newmethod
from pypy.objspace.std.stdtypedef import StdObjSpaceMultiMethod

# ERRORCODES

ERR_WRONG_SECOND = "complex() can't take second arg if first is a string"
ERR_MALFORMED = "complex() arg is a malformed string"

OVERFLOWED_FLOAT = 1e200
OVERFLOWED_FLOAT *= OVERFLOWED_FLOAT

complex_conjugate = StdObjSpaceMultiMethod('conjugate', 1)

register_all(vars(),globals())

def _split_complex(s):
    slen = len(s)
    if slen == 0:
        raise ValueError
    realstart = 0
    realstop = 0
    imagstart = 0
    imagstop = 0
    imagsign = ' '
    i = 0
    # ignore whitespace
    while i < slen and s[i] == ' ':
        i += 1

    # extract first number
    realstart = i
    pc = s[i]
    while i < slen and s[i] != ' ': 
        if s[i] in ('+','-') and pc not in ('e','E') and i != realstart:
            break
        pc = s[i]
        i += 1

    realstop = i

    # ignore whitespace
    while i < slen and s[i] == ' ':
        i += 1

    # return appropriate strings is only one number is there
    if i >= slen:
        newstop = realstop - 1
        if newstop < 0:
            raise ValueError
        if s[newstop] in ('j','J'):
            if realstart == newstop:
                imagpart = '1.0'
            else:
                imagpart = s[realstart:newstop]
            return '0.0', imagpart
        else:
            return s[realstart:realstop],'0.0'

    # find sign for imaginary part
    if s[i] == '-' or s[i] == '+':
        imagsign = s[i]
    if imagsign == ' ':
        raise ValueError

    i+=1
    # whitespace
    while i < slen and s[i] == ' ':
        i += 1
    if i >= slen:
        raise ValueError

    imagstart = i
    pc = s[i]
    while i < slen and s[i] != ' ':
        if s[i] in ('+','-') and pc not in ('e','E'):
            break
        pc = s[i]
        i += 1

    imagstop = i - 1
    if imagstop < 0:
        raise ValueError
    if s[imagstop] not in ('j','J'):
        raise ValueError
    if imagstop < imagstart:
        raise ValueError

    while i<slen and s[i] == ' ':
        i += 1
    if i <  slen:
        raise ValueError

    realpart = s[realstart:realstop]
    if imagstart == imagstop:
        imagpart = '1.0'
    else:
        imagpart = s[imagstart:imagstop]
    if imagsign == '-':
        imagpart = imagsign + imagpart

    return realpart, imagpart


def check_second_arg(space, w_c):
    """check, if second 'complex' argument is a string"""
    if space.is_true(space.isinstance(w_c, space.w_str)):
        raise TypeError()
    return True

def simple_arg_check(space, w_r, w_c):
    """check, if there is a second argument, if first is a string"""
    if space.is_true(space.isinstance(w_r, space.w_str)) or \
            space.is_true(space.isinstance(w_r, space.w_unicode)):
        if not space.eq_w(w_c,space.w_None):
            raise TypeError

def descr__new__(space, w_complextype, w_real=0.0, w_imag=None):
    
    from pypy.objspace.std.complexobject import W_ComplexObject

    try:
        check_second_arg(space, w_imag)
    except TypeError:
        raise OperationError(space.w_TypeError,space.wrap("complex() second arg can't be a string"))
    try:
        simple_arg_check(space, w_real, w_imag)
    except TypeError:
        raise OperationError(space.w_TypeError, space.wrap(ERR_WRONG_SECOND))
    # if arguments can be cast to a float, do it
    if space.is_w(w_complextype, space.w_complex) and \
        space.eq_w(space.type(w_real), space.w_complex) and \
        space.eq_w(w_imag, space.w_None):
        # common case
        return w_real 

    if space.is_true(space.isinstance(w_real, space.w_str)) or \
            space.is_true(space.isinstance(w_real, space.w_unicode)):
        try:
            realstr, imagstr = _split_complex(space.str_w(w_real))

        except ValueError:
            raise OperationError(space.w_ValueError, space.wrap(ERR_MALFORMED))
        try:
            realval = interp_string_to_float(space, realstr)
            imagval = interp_string_to_float(space, imagstr)
        except ParseStringError:
            raise OperationError(space.w_ValueError, space.wrap(ERR_MALFORMED))
        else:
            #check for overflow            
            if abs(realval) == OVERFLOWED_FLOAT or abs(imagval) == OVERFLOWED_FLOAT:
                raise OperationError(space.w_ValueError,space.wrap(
                                    "complex() literal too large to convert"))
            if space.is_w(w_complextype, space.w_complex):
                # common case
                w_obj = W_ComplexObject(realval, imagval)
            else:
                # We are dealing with a subclass of complex
                w_obj = space.allocate_instance(W_ComplexObject, w_complextype)
                W_ComplexObject.__init__(w_obj,realval, imagval)

            return w_obj
    # w_imag is now either float or None
    # w_real is either string, complex or float
    # test for '__complex__' attribute and get result of
    # __complex__ method
    w_complex_first = extract_complex(space, w_real)
    if not space.eq_w(w_complex_first, space.w_None):
        w_real = w_complex_first
    
    # if w_real is a complex number and there is no second
    # argument, return w_real after checking the type
    if space.is_true(space.isinstance(w_real, space.w_complex)):
        if not space.eq_w(w_imag, space.w_None):
            if not space.is_true(space.isinstance(w_imag, space.w_complex)):
                w_imag = space.call_function(space.w_float,w_imag)
            w_tmp = space.newcomplex(0, 1)
            w_tmp = space.mul(w_tmp,w_imag)
            w_real  = space.add(w_real,w_tmp)

    elif not space.is_true(space.isinstance(w_real, space.w_str)):
        if space.eq_w(w_imag, space.w_None):
            w_imag = space.wrap(0)
        w_real = space.call_function(space.w_float,w_real)
        if not space.is_true(space.isinstance(w_imag, space.w_complex)):
            w_imag = space.call_function(space.w_float,w_imag)
        tmp = space.newcomplex(0, 1)
        w_imag = space.mul(w_imag,tmp)
        w_real = space.add(w_real,w_imag)
    if space.is_w(w_complextype, space.w_complex):
        # common case
        w_obj = W_ComplexObject(w_real.realval,w_real.imagval)
    else:
        # We are dealing with a subclass of complex
        w_obj = space.allocate_instance(W_ComplexObject, w_complextype)
        W_ComplexObject.__init__(w_obj, w_real.realval, w_real.imagval)
    return w_obj
        
app = gateway.applevel(r"""
def extract_complex(num):
    if not hasattr(num,'__complex__'):
        return None
    cnum = num.__complex__()
    if isinstance(cnum,complex):
        return cnum
    else:
        return None
""", filename=__file__)

extract_complex = app.interphook('extract_complex')

def complexwprop(name):
    def fget(space, w_obj):
        from pypy.objspace.std.complexobject import W_ComplexObject
        if not isinstance(w_obj, W_ComplexObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("descriptor is for 'complex'"))
        return space.newfloat(getattr(w_obj, name))
    return GetSetProperty(fget)

complex_typedef = StdTypeDef("complex",
    __doc__ = """complex(real[, imag]) -> complex number
        
Create a complex number from a real part and an optional imaginary part.
This is equivalent to (real + imag*1j) where imag defaults to 0.""",
    __new__ = newmethod(descr__new__),
    real = complexwprop('realval'),
    imag = complexwprop('imagval'),
    )

complex_typedef.custom_hash = True
complex_typedef.registermethods(globals())
