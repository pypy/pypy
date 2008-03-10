"""
This module defines mappings between operation names and Python's
built-in functions (or type constructors) implementing them.
"""
from pypy.interpreter.baseobjspace import ObjSpace
import operator, types, __future__
from pypy.tool.sourcetools import compile2
from pypy.rlib.rarithmetic import ovfcheck, ovfcheck_lshift

FunctionByName = {}   # dict {"operation_name": <built-in function>}
OperationName  = {}   # dict {<built-in function>: "operation_name"}
Arity          = {}   # dict {"operation name": number of arguments}

# ____________________________________________________________

def new_style_type(x):
    """Simulate a situation where every class is new-style"""
    t = getattr(x, '__class__', type(x))
    if t is types.ClassType:   # guess who's here?  exception classes...
        t = type
    return t

def do_int(x):
    return x.__int__()

def do_index(x):
    return x.__index__()

def do_float(x):
    return x.__float__()

def do_long(x):
    return x.__long__()

def inplace_add(x, y):
    x += y
    return x

def inplace_sub(x, y):
    x -= y
    return x

def inplace_mul(x, y):
    x *= y
    return x

exec compile2("""
def inplace_truediv(x, y):
    x /= y
    return x
""", flags=__future__.CO_FUTURE_DIVISION, dont_inherit=1)
#                     makes an INPLACE_TRUE_DIVIDE

def inplace_floordiv(x, y):
    x //= y
    return x

exec compile2("""
def inplace_div(x, y):
    x /= y
    return x
""", flags=0, dont_inherit=1)    # makes an INPLACE_DIVIDE

def inplace_mod(x, y):
    x %= y
    return x

def inplace_pow(x, y):
    x **= y
    return x

def inplace_lshift(x, y):
    x <<= y
    return x

def inplace_rshift(x, y):
    x >>= y
    return x

def inplace_and(x, y):
    x &= y
    return x

def inplace_or(x, y):
    x |= y
    return x

def inplace_xor(x, y):
    x ^= y
    return x

def next(x):
    return x.next()

def get(x, y, z=None):
    return x.__get__(y, z)

def set(x, y, z):
    x.__set__(y, z)

def delete(x, y):
    x.__delete__(y)

def userdel(x):
    x.__del__()

def neg_ovf(x):
    return ovfcheck(-x)

def abs_ovf(x):
    return ovfcheck(abs(x))

def add_ovf(x, y):
    return ovfcheck(x + y)

def sub_ovf(x, y):
    return ovfcheck(x - y)

def mul_ovf(x, y):
    return ovfcheck(x * y)

def floordiv_ovf(x, y):
    return ovfcheck(operator.floordiv(x, y))

def div_ovf(x, y):
    return ovfcheck(operator.div(x, y))

def mod_ovf(x, y):
    return ovfcheck(x % y)

##def pow_ovf(*two_or_three_args):
##    return ovfcheck(pow(*two_or_three_args))

def lshift_ovf(x, y):
    return ovfcheck_lshift(x, y)

# ____________________________________________________________

# The following table can list several times the same operation name,
# if multiple built-in functions correspond to it.  The first one should
# be picked, though, as the best built-in for the given operation name.
# Lines ('name', operator.name) are added automatically.

# INTERNAL ONLY, use the dicts declared at the top of the file.
Table = [
    ('id',              id),
    ('type',            new_style_type),
    ('type',            type),
    ('issubtype',       issubclass),
    ('repr',            repr),
    ('str',             str),
    ('len',             len),
    ('hash',            hash),
    ('getattr',         getattr),
    ('setattr',         setattr),
    ('delattr',         delattr),
    ('nonzero',         bool),
    ('nonzero',         operator.truth),
    ('is_true',         bool),
    ('is_true',         operator.truth),
    ('abs' ,            abs),
    ('hex',             hex),
    ('oct',             oct),
    ('ord',             ord),
    ('divmod',          divmod),
    ('pow',             pow),
    ('int',             do_int),
    ('index',           do_index),
    ('float',           do_float),
    ('long',            do_long),
    ('inplace_add',     inplace_add),
    ('inplace_sub',     inplace_sub),
    ('inplace_mul',     inplace_mul),
    ('inplace_truediv', inplace_truediv),
    ('inplace_floordiv',inplace_floordiv),
    ('inplace_div',     inplace_div),
    ('inplace_mod',     inplace_mod),
    ('inplace_pow',     inplace_pow),
    ('inplace_lshift',  inplace_lshift),
    ('inplace_rshift',  inplace_rshift),
    ('inplace_and',     inplace_and),
    ('inplace_or',      inplace_or),
    ('inplace_xor',     inplace_xor),
    ('cmp',             cmp),
    ('coerce',          coerce),
    ('iter',            iter),
    ('next',            next),
    ('get',             get),
    ('set',             set),
    ('delete',          delete),
    ('userdel',         userdel),
    ('buffer',          buffer),
    # --- operations added by graph transformations ---
    ('neg_ovf',         neg_ovf),
    ('abs_ovf',         abs_ovf),
    ('add_ovf',         add_ovf),
    ('sub_ovf',         sub_ovf),
    ('mul_ovf',         mul_ovf),
    ('floordiv_ovf',    floordiv_ovf),
    ('div_ovf',         div_ovf),
    ('mod_ovf',         mod_ovf),
    ('lshift_ovf',      lshift_ovf),
    ]

def setup():
    if not hasattr(operator, 'is_'):   # Python 2.2
        Table.append(('is_', lambda x, y: x is y))
    # insert all operators
    for line in ObjSpace.MethodTable:
        name = line[0]
        if hasattr(operator, name):
            Table.append((name, getattr(operator, name)))
    # build the dictionaries
    for name, func in Table:
        if name not in FunctionByName:
            FunctionByName[name] = func
        if func not in OperationName:
            OperationName[func] = name
    # check that the result is complete
    for line in ObjSpace.MethodTable:
        name = line[0]
        Arity[name] = line[2]
        assert name in FunctionByName
setup()
del Table   # INTERNAL ONLY, use the dicts declared at the top of the file
