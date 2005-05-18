"""
This module defines mappings between operation names and Python's
built-in functions (or type constructors) implementing them.
"""
from pypy.interpreter.baseobjspace import ObjSpace
import operator, types, __future__
from pypy.tool.sourcetools import compile2

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

# ____________________________________________________________

# The following table can list several times the same operation name,
# if multiple built-in functions correspond to it.  The first one should
# be picked, though, as the best built-in for the given operation name.
# Lines ('name', operator.name) are added automatically.
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
    ('abs' ,            abs),
    ('hex',             hex),
    ('oct',             oct),
    ('ord',             ord),
    ('divmod',          divmod),
    ('pow',             pow),
    ('int',             do_int),
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
        assert func not in OperationName
        OperationName[func] = name
    # check that the result is complete
    for line in ObjSpace.MethodTable:
        name = line[0]
        Arity[name] = line[2]
        assert name in FunctionByName
setup()
