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

complex_conjugate = StdObjSpaceMultiMethod('conjugate', 1,
                                           doc="(A+Bj).conjugate() -> A-Bj")

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


def descr__new__(space, w_complextype, w_real=0.0, w_imag=None):
    from pypy.objspace.std.complexobject import W_ComplexObject

    # if w_real is already a complex number and there is no second
    # argument, return it.  Note that we cannot return w_real if
    # it is an instance of a *subclass* of complex, or if w_complextype
    # is itself a subclass of complex.
    noarg2 = space.is_w(w_imag, space.w_None)
    if (noarg2 and space.is_w(w_complextype, space.w_complex)
               and space.is_w(space.type(w_real), space.w_complex)):
        return w_real

    if space.is_true(space.isinstance(w_real, space.w_str)) or \
            space.is_true(space.isinstance(w_real, space.w_unicode)):
        # a string argument
        if not noarg2:
            raise OperationError(space.w_TypeError,
                                 space.wrap("complex() can't take second arg"
                                            " if first is a string"))
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

    else:
        # non-string arguments

        # test for a '__complex__' method, and call it if found.
        # A bit of a hack to support old-style classes: don't use
        # space.lookup() (this is similar to CPython).
        try:
            w_method = space.getattr(w_real, space.wrap('__complex__'))
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
        else:
            w_real = space.call_function(w_method)
            # __complex__() could return a string, which space.float()
            # could accept below...  Let's catch this case.
            if space.is_true(space.isinstance(w_imag, space.w_str)) or \
                   space.is_true(space.isinstance(w_imag, space.w_unicode)):
                raise OperationError(space.w_TypeError,
                                     space.wrap("__complex__() cannot return"
                                                " a string"))

        # at this point w_real can be an instance of 'complex',
        # either because it is the result of __complex__() or because
        # the shortcut at the beginning of the function didn't match
        if space.is_true(space.isinstance(w_real, space.w_complex)):
            # note that we are unwrapping the complex for the rest of
            # the code.  This also ensures that we eventually return
            # an object of the correct subclass of complex.
            realval = space.float_w(space.getattr(w_real, space.wrap('real')))
            imagval = space.float_w(space.getattr(w_real, space.wrap('imag')))
        else:
            realval = space.float_w(space.float(w_real))
            imagval = 0.0

        # now take w_imag into account
        if not noarg2:
            if space.is_true(space.isinstance(w_imag, space.w_complex)):
                # complex(x, y) == x+y*j, even if 'y' is already a complex.
                # say y == a+b*j:
                a = space.float_w(space.getattr(w_imag, space.wrap('real')))
                b = space.float_w(space.getattr(w_imag, space.wrap('imag')))
                realval -= b
                imagval += a
            elif space.is_true(space.isinstance(w_imag, space.w_str)) or \
                     space.is_true(space.isinstance(w_imag, space.w_unicode)):
                # prevent space.float(w_imag) from succeeding
                raise OperationError(space.w_TypeError,
                                     space.wrap("complex() second arg"
                                                " can't be a string"))
            else:
                imagval += space.float_w(space.float(w_imag))
    # done
    w_obj = space.allocate_instance(W_ComplexObject, w_complextype)
    W_ComplexObject.__init__(w_obj, realval, imagval)
    return w_obj

def complexwprop(name):
    def fget(space, w_obj):
        from pypy.objspace.std.complexobject import W_ComplexObject
        if not isinstance(w_obj, W_ComplexObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("descriptor is for 'complex'"))
        return space.newfloat(getattr(w_obj, name))
    return GetSetProperty(fget)
    
def descr___getnewargs__(space,  w_self):
    from pypy.objspace.std.complexobject import W_ComplexObject
    assert isinstance(w_self, W_ComplexObject)
    return space.newtuple([space.newcomplex(w_self.realval,w_self.imagval)]) 
    
complex_typedef = StdTypeDef("complex",
    __doc__ = """complex(real[, imag]) -> complex number
        
Create a complex number from a real part and an optional imaginary part.
This is equivalent to (real + imag*1j) where imag defaults to 0.""",
    __new__ = newmethod(descr__new__),
    __getnewargs__ = newmethod(descr___getnewargs__),
    real = complexwprop('realval'),
    imag = complexwprop('imagval'),
    )

complex_typedef.custom_hash = True
complex_typedef.registermethods(globals())
