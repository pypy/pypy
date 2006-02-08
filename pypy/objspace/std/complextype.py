import pypy.objspace.std.stdtypedef as poss
from pypy.interpreter.error import OperationError
from pypy.objspace.std.strutil import interp_string_to_float, ParseStringError
from pypy.objspace.std.noneobject import W_NoneObject

# ERRORCODES

ERR_WRONG_SECOND = "complex() can't take second arg if first is a string"
ERR_MALFORMED = "complex() arg is a malformed string"

def _split_complex(s):
    s = s.replace(' ','')
    slen = len(s)
    realnum = '0.0'
    imagnum = '0.0'
    pc = ''
    i = 0
    bp = 0
    while i < slen:
        c = s[i]
        if c in ('+','-') and pc not in ('e','E'):
            bp = i
            break
        pc = c
        i += 1
    if bp:
        if s[-1] not in ['j','J']:
            raise ValueError('complex() arg is a malformed string')
        realnum = s[:bp]
        imagnum = s[bp+1:-1]
    else:
        if s[-1] in ['j','J']:
            imagnum = s[:-1]
        else:
            realnum = s

    return realnum, imagnum



def check_second_arg(space, w_c):
    if space.is_true(space.isinstance(w_c, space.w_str)):
        raise TypeError()
    return True

def descr__new__(space, w_complextype, w_real=0.0, w_imag=None):
    from pypy.objspace.std.complexobject import W_ComplexObject
    # @@ bad hack
    try:
        w_real = space.call_method(w_real,'__complex__')
    except OperationError:pass
    # @@ end bad hack
    try:
        check_second_arg(space, w_imag)
    except TypeError:
        raise OperationError(space.w_TypeError,space.wrap("complex() second arg can't be a string"))

    if space.is_true(space.isinstance(w_real, space.w_complex)) and \
            space.eq_w(w_imag, space.w_None):
        return w_real
    elif not space.is_true(space.isinstance(w_real, space.w_str)) and \
            not space.eq_w(w_imag, space.w_None):
        w_imag = space.mul(w_imag,space.newcomplex(0.0,1.0))
        return space.add(w_real,w_imag)
    if space.is_true(space.isinstance(w_real, space.w_str)) or \
            space.is_true(space.isinstance(w_real, space.w_unicode)):
        if not space.eq_w(w_imag,space.w_None):
            raise OperationError(space.w_ValueError, 
                    space.wrap(ERR_WRONG_SECOND))
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
        if space.eq_w(w_imag,space.w_None):
            w_imag = space.wrap(0.0)
        try:
            realval = space.float_w(w_real)
            imagval = space.float_w(w_imag)
        except ValueError, e:
            raise OperationError(space.w_ValueError, space.wrap(e.msg))
    w_obj = space.allocate_instance(W_ComplexObject, w_complextype)
    W_ComplexObject.__init__(w_obj, space, realval, imagval)

    return w_obj

def descr_conjugate(space, w_self):
    from pypy.objspace.std.complexobject import W_ComplexObject
    return W_ComplexObject(space,w_self._real, -w_self._imag)

def complexwprop(name):
    def fget(space, w_obj):
        from pypy.objspace.std.complexobject import W_ComplexObject
        if not isinstance(w_obj, W_ComplexObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("descriptor is for 'complex'"))
        return space.newfloat(getattr(w_obj, name))
    return poss.GetSetProperty(fget)

complex_typedef = poss.StdTypeDef("complex",
    __doc__ = """complex(real[, imag]) -> complex number
        
Create a complex number from a real part and an optional imaginary part.
This is equivalent to (real + imag*1j) where imag defaults to 0.""",
    __new__ = poss.newmethod(descr__new__),
    real = complexwprop('_real'),
    imag = complexwprop('_imag'),
    conjugate = poss.newmethod(descr_conjugate)
    )
