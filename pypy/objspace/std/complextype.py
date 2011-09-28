from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.strutil import string_to_float, ParseStringError
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.stdtypedef import GetSetProperty, StdTypeDef
from pypy.objspace.std.stdtypedef import StdObjSpaceMultiMethod

# ERRORCODES

ERR_WRONG_SECOND = "complex() can't take second arg if first is a string"
ERR_MALFORMED = "complex() arg is a malformed string"

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

    if s[i] == '(' and s[slen-1] == ')':
        i += 1
        slen -= 1
        # ignore whitespace after bracket
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
        if s[newstop] in ('j', 'J'):
            if realstart == newstop:
                imagpart = '1.0'
            elif realstart == newstop-1 and s[realstart] == '+':
                imagpart = '1.0'
            elif realstart == newstop-1 and s[realstart] == '-':
                imagpart = '-1.0'
            else:
                imagpart = s[realstart:newstop]
            return '0.0', imagpart
        else:
            return s[realstart:realstop], '0.0'

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

    if space.isinstance_w(w_real, space.w_str) or \
            space.isinstance_w(w_real, space.w_unicode):
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
            realval = string_to_float(realstr)
            imagval = string_to_float(imagstr)
        except ParseStringError:
            raise OperationError(space.w_ValueError, space.wrap(ERR_MALFORMED))

    else:
        # non-string arguments
        realval, imagval = unpackcomplex(space, w_real)

        # now take w_imag into account
        if not noarg2:
            # complex(x, y) == x+y*j, even if 'y' is already a complex.
            realval2, imagval2 = unpackcomplex(space, w_imag)

            # try to preserve the signs of zeroes of realval and realval2
            if imagval2 != 0.0:
                realval -= imagval2

            if imagval != 0.0:
                imagval += realval2
            else:
                imagval = realval2
    # done
    w_obj = space.allocate_instance(W_ComplexObject, w_complextype)
    W_ComplexObject.__init__(w_obj, realval, imagval)
    return w_obj


def unpackcomplex(space, w_complex):
    from pypy.objspace.std.complexobject import W_ComplexObject
    if type(w_complex) is W_ComplexObject:
        return (w_complex.realval, w_complex.imagval)
    #
    # test for a '__complex__' method, and call it if found.
    # special case old-style instances, like CPython does.
    w_z = None
    if space.is_oldstyle_instance(w_complex):
        try:
            w_method = space.getattr(w_complex, space.wrap('__complex__'))
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
        else:
            w_z = space.call_function(w_method)
    else:
        w_method = space.lookup(w_complex, '__complex__')
        if w_method is not None:
            w_z = space.get_and_call_function(w_method, w_complex)
    #
    if w_z is not None:
        # __complex__() must return a complex object
        # (XXX should not use isinstance here)
        if not isinstance(w_z, W_ComplexObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("__complex__() must return"
                                            " a complex number"))
        return (w_z.realval, w_z.imagval)
    #
    # no '__complex__' method, so we assume it is a float,
    # unless it is an instance of some subclass of complex.
    if isinstance(w_complex, W_ComplexObject):
        return (w_complex.realval, w_complex.imagval)
    #
    # Check that it is not a string (on which space.float() would succeed).
    if (space.isinstance_w(w_complex, space.w_str) or
        space.isinstance_w(w_complex, space.w_unicode)):
        raise operationerrfmt(space.w_TypeError,
                              "complex number expected, got '%s'",
                              space.type(w_complex).getname(space))
    #
    return (space.float_w(space.float(w_complex)), 0.0)


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
    return space.newtuple([space.newfloat(w_self.realval),
                           space.newfloat(w_self.imagval)])

complex_typedef = StdTypeDef("complex",
    __doc__ = """complex(real[, imag]) -> complex number

Create a complex number from a real part and an optional imaginary part.
This is equivalent to (real + imag*1j) where imag defaults to 0.""",
    __new__ = gateway.interp2app(descr__new__),
    __getnewargs__ = gateway.interp2app(descr___getnewargs__),
    real = complexwprop('realval'),
    imag = complexwprop('imagval'),
    )

complex_typedef.registermethods(globals())
