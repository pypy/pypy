import sys
from pypy.rlib.rarithmetic import r_longlong, r_uint, intmask
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.lltype import Signed, SignedLongLong, \
                                        UnsignedLongLong

#XXX original SIGNED_RIGHT_SHIFT_ZERO_FILLS not taken into account
#XXX assuming HAVE_LONG_LONG (int_mul_ovf)
#XXX should int_mod and int_floordiv return an intmask(...) instead?

LONG_MAX = sys.maxint
LONG_MIN = -sys.maxint-1

LLONG_MAX = r_longlong(2 ** (r_longlong.BITS-1) - 1)
LLONG_MIN = -LLONG_MAX-1

def int_floordiv_zer(x, y):
    '''#define OP_INT_FLOORDIV_ZER(x,y,r,err) \
        if ((y)) { OP_INT_FLOORDIV(x,y,r,err); } \
        else FAIL_ZER(err, "integer division")
    '''
    if y:
        return llop.int_floordiv(Signed, x, y)
    else:
        raise ZeroDivisionError("integer division")

def uint_floordiv_zer(x, y):
    '''#define OP_UINT_FLOORDIV_ZER(x,y,r,err) \
        if ((y)) { OP_UINT_FLOORDIV(x,y,r,err); } \
        else FAIL_ZER(err, "unsigned integer division")
    '''
    if y:
        return x / y
    else:
        raise ZeroDivisionError("unsigned integer division")

def llong_floordiv_zer(x, y):
    '''#define OP_LLONG_FLOORDIV_ZER(x,y,r) \
      if ((y)) { OP_LLONG_FLOORDIV(x,y,r); } \
      else FAIL_ZER("integer division")
    '''
    if y:
        return llop.llong_floordiv(SignedLongLong, x, y)
    else:
        raise ZeroDivisionError("integer division")

def ullong_floordiv_zer(x, y):
    '''#define OP_ULLONG_FLOORDIV_ZER(x,y,r) \
      if ((y)) { OP_ULLONG_FLOORDIV(x,y,r); } \
      else FAIL_ZER("unsigned integer division")
    '''
    if y:
        return llop.llong_floordiv(UnsignedLongLong, x, y)
    else:
        raise ZeroDivisionError("unsigned integer division")


def int_neg_ovf(x):
    if x == LONG_MIN:
        raise OverflowError("integer negate")
    return -x

def llong_neg_ovf(x):
    if x == LLONG_MIN:
        raise OverflowError("integer negate")
    return -x

def int_abs_ovf(x):
    if x == LONG_MIN:
        raise OverflowError("integer absolute")
    if x < 0:
        return -x
    else:
        return x

def llong_abs_ovf(x):
    if x == LLONG_MIN:
        raise OverflowError("integer absolute")
    if x < 0:
        return -x
    else:
        return x

def int_add_ovf(x, y):
    '''#define OP_INT_ADD_OVF(x,y,r,err) \
        OP_INT_ADD(x,y,r,err); \
        if ((r^(x)) >= 0 || (r^(y)) >= 0); \
        else FAIL_OVF(err, "integer addition")
    '''
    r = x + y
    if r^x >= 0 or r^y >= 0:
        return r
    else:
        raise OverflowError("integer addition")

def int_add_nonneg_ovf(x, y):
    '''
    OP_INT_ADD(x,y,r); \
    if (r >= (x)); \
    else FAIL_OVF("integer addition")
    '''
    r = x + y
    if r >= x:
        return r
    else:
        raise OverflowError("integer addition")

def int_sub_ovf(x, y):
    '''#define OP_INT_SUB_OVF(x,y,r,err) \
        OP_INT_SUB(x,y,r,err); \
        if ((r^(x)) >= 0 || (r^~(y)) >= 0); \
        else FAIL_OVF(err, "integer subtraction")
    '''
    r = x - y
    if r^x >= 0 or r^~y >= 0:
        return r
    else:
        raise OverflowError("integer subtraction")

def int_lshift_ovf(x, y):
    '''#define OP_INT_LSHIFT_OVF(x,y,r,err) \
        OP_INT_LSHIFT(x,y,r,err); \
        if ((x) != Py_ARITHMETIC_RIGHT_SHIFT(long, r, (y))) \
                FAIL_OVF(err, "x<<y losing bits or changing sign")
    '''
    r = x << y
    if x != _Py_ARITHMETIC_RIGHT_SHIFT(r, y):
        raise OverflowError("x<<y losing bits or changing sign")
    else:
        return r

def int_rshift_val(x, y):
    '''#define OP_INT_RSHIFT_VAL(x,y,r,err) \
        if ((y) >= 0) { OP_INT_RSHIFT(x,y,r,err); } \
        else FAIL_VAL(err, "negative shift count")
    '''
    if y >= 0:
        return _Py_ARITHMETIC_RIGHT_SHIFT(x, y)
    else:
        raise ValueError("negative shift count")

def int_lshift_val(x, y):
    '''#define OP_INT_LSHIFT_VAL(x,y,r,err) \
        if ((y) >= 0) { OP_INT_LSHIFT(x,y,r,err); } \
        else FAIL_VAL(err, "negative shift count")
    '''
    if y >= 0:
        return x << y
    else:
        raise ValueError("negative shift count")

def int_lshift_ovf_val(x, y):
    '''#define OP_INT_LSHIFT_OVF_VAL(x,y,r,err) \
        if ((y) >= 0) { OP_INT_LSHIFT_OVF(x,y,r,err); } \
        else FAIL_VAL(err, "negative shift count")
    '''
    if y >= 0:
        return int_lshift_ovf(x, y)
    else:
        raise ValueError("negative shift count")

def int_floordiv_ovf(x, y):
    '''#define OP_INT_FLOORDIV_OVF(x,y,r,err) \
        if ((y) == -1 && (x) < 0 && ((unsigned long)(x) << 1) == 0) \
                FAIL_OVF(err, "integer division"); \
        OP_INT_FLOORDIV(x,y,r,err)
    '''
    if y == -1 and x < 0 and (r_uint(x) << 1) == 0:
        raise OverflowError("integer division")
    else:
        return llop.int_floordiv(Signed, x, y)

def int_floordiv_ovf_zer(x, y):
    '''#define OP_INT_FLOORDIV_OVF_ZER(x,y,r,err) \
        if ((y)) { OP_INT_FLOORDIV_OVF(x,y,r,err); } \
        else FAIL_ZER(err, "integer division")
    '''
    if y:
        return int_floordiv_ovf(x, y)
    else:
        raise ZeroDivisionError("integer division")

def int_mod_ovf(x, y):
    '''#define OP_INT_MOD_OVF(x,y,r,err) \
        if ((y) == -1 && (x) < 0 && ((unsigned long)(x) << 1) == 0) \
                FAIL_OVF(err, "integer modulo"); \
        OP_INT_MOD(x,y,r,err)
    '''
    if y == -1 and x < 0 and (r_uint(x) << 1) == 0:
        raise OverflowError("integer modulo")
    else:
        return llop.int_mod(Signed, x, y)

def int_mod_zer(x, y):
    '''#define OP_INT_MOD_ZER(x,y,r,err) \
        if ((y)) { OP_INT_MOD(x,y,r,err); } \
        else FAIL_ZER(err, "integer modulo")
    '''
    if y:
        return llop.int_mod(Signed, x, y)
    else:
        raise ZeroDivisionError("integer modulo")

def uint_mod_zer(x, y):
    '''#define OP_UINT_MOD_ZER(x,y,r,err) \
        if ((y)) { OP_UINT_MOD(x,y,r,err); } \
        else FAIL_ZER(err, "unsigned integer modulo")
    '''
    if y:
        return x % y
    else:
        raise ZeroDivisionError("unsigned integer modulo")

def int_mod_ovf_zer(x, y):
    '''#define OP_INT_MOD_OVF_ZER(x,y,r,err) \
        if ((y)) { OP_INT_MOD_OVF(x,y,r,err); } \
        else FAIL_ZER(err, "integer modulo")
    '''
    if y:
        return int_mod_ovf(x, y)
    else:
        raise ZeroDivisionError("integer modulo")

def llong_mod_zer(x, y):
    '''#define OP_LLONG_MOD_ZER(x,y,r) \
      if ((y)) { OP_LLONG_MOD(x,y,r); } \
      else FAIL_ZER("integer modulo")
    '''
    if y:
        return llop.int_mod(SignedLongLong, x, y)
    else:
        raise ZeroDivisionError("integer modulo")

# Helpers...

def _Py_ARITHMETIC_RIGHT_SHIFT(i, j):
    '''
// Py_ARITHMETIC_RIGHT_SHIFT
// C doesn't define whether a right-shift of a signed integer sign-extends
// or zero-fills.  Here a macro to force sign extension:
// Py_ARITHMETIC_RIGHT_SHIFT(TYPE, I, J)
//    Return I >> J, forcing sign extension.
// Requirements:
//    I is of basic signed type TYPE (char, short, int, long, or long long).
//    TYPE is one of char, short, int, long, or long long, although long long
//    must not be used except on platforms that support it.
//    J is an integer >= 0 and strictly less than the number of bits in TYPE
//    (because C doesn't define what happens for J outside that range either).
// Caution:
//    I may be evaluated more than once.

#ifdef SIGNED_RIGHT_SHIFT_ZERO_FILLS
    #define Py_ARITHMETIC_RIGHT_SHIFT(TYPE, I, J) \
            ((I) < 0 ? ~((~(unsigned TYPE)(I)) >> (J)) : (I) >> (J))
#else
    #define Py_ARITHMETIC_RIGHT_SHIFT(TYPE, I, J) ((I) >> (J))
#endif
    '''
    return i >> j

#XXX some code from src/int.h seems missing
#def int_mul_ovf(x, y): #HAVE_LONG_LONG version
#    '''{ \
#        PY_LONG_LONG lr = (PY_LONG_LONG)(x) * (PY_LONG_LONG)(y); \
#        r = (long)lr; \
#        if ((PY_LONG_LONG)r == lr); \
#        else FAIL_OVF(err, "integer multiplication"); \
#    }
#    '''
#    lr = r_longlong(x) * r_longlong(y);
#    r  = intmask(lr)
#    if r_longlong(r) == lr:
#        return r
#    else:
#        raise OverflowError("integer multiplication")

#not HAVE_LONG_LONG version
def int_mul_ovf(a, b):          #long a, long b, long *longprod):
    longprod = a * b
    doubleprod = float(a) * float(b)
    doubled_longprod = float(longprod)

    # Fast path for normal case:  small multiplicands, and no info is lost in either method.
    if doubled_longprod == doubleprod:
        return longprod

    # Somebody somewhere lost info.  Close enough, or way off?  Note
    # that a != 0 and b != 0 (else doubled_longprod == doubleprod == 0).
    # The difference either is or isn't significant compared to the
    # true value (of which doubleprod is a good approximation).
    # absdiff/absprod <= 1/32 iff 32 * absdiff <= absprod -- 5 good bits is "close enough"
    if 32.0 * abs(doubled_longprod - doubleprod) <= abs(doubleprod):
        return longprod

    raise OverflowError("integer multiplication")
