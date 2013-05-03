"""
This module defines mappings between operation names and Python's
built-in functions (or type constructors) implementing them.
"""

import __builtin__
import __future__
import operator
from rpython.tool.sourcetools import compile2
from rpython.rlib.rarithmetic import ovfcheck

class _OpHolder(object): pass
op = _OpHolder()

class SpaceOperator(object):
    def __init__(self, name, arity, symbol):
        self.name = name
        self.arity = arity
        self.symbol = symbol

def add_operator(name, arity, symbol):
    operator = SpaceOperator(name, arity, symbol)
    setattr(op, name, operator)

add_operator('is_', 2, 'is')
add_operator('id', 1, 'id')
add_operator('type', 1, 'type')
add_operator('isinstance', 2, 'isinstance')
add_operator('issubtype', 2, 'issubtype')  # not for old-style classes
add_operator('repr', 1, 'repr')
add_operator('str', 1, 'str')
add_operator('format', 2, 'format')
add_operator('len', 1, 'len')
add_operator('hash', 1, 'hash')
add_operator('getattr', 2, 'getattr')
add_operator('setattr', 3, 'setattr')
add_operator('delattr', 2, 'delattr')
add_operator('getitem', 2, 'getitem')
add_operator('setitem', 3, 'setitem')
add_operator('delitem', 2, 'delitem')
add_operator('getslice', 3, 'getslice')
add_operator('setslice', 4, 'setslice')
add_operator('delslice', 3, 'delslice')
add_operator('trunc', 1, 'trunc')
add_operator('pos', 1, 'pos')
add_operator('neg', 1, 'neg')
add_operator('nonzero', 1, 'truth')
add_operator('abs' , 1, 'abs')
add_operator('hex', 1, 'hex')
add_operator('oct', 1, 'oct')
add_operator('ord', 1, 'ord')
add_operator('invert', 1, '~')
add_operator('add', 2, '+')
add_operator('sub', 2, '-')
add_operator('mul', 2, '*')
add_operator('truediv', 2, '/')
add_operator('floordiv', 2, '//')
add_operator('div', 2, 'div')
add_operator('mod', 2, '%')
add_operator('divmod', 2, 'divmod')
add_operator('pow', 3, '**')
add_operator('lshift', 2, '<<')
add_operator('rshift', 2, '>>')
add_operator('and_', 2, '&')
add_operator('or_', 2, '|')
add_operator('xor', 2, '^')
add_operator('int', 1, 'int')
add_operator('index', 1, 'index')
add_operator('float', 1, 'float')
add_operator('long', 1, 'long')
add_operator('inplace_add', 2, '+=')
add_operator('inplace_sub', 2, '-=')
add_operator('inplace_mul', 2, '*=')
add_operator('inplace_truediv', 2, '/=')
add_operator('inplace_floordiv', 2, '//=')
add_operator('inplace_div', 2, 'div=')
add_operator('inplace_mod', 2, '%=')
add_operator('inplace_pow', 2, '**=')
add_operator('inplace_lshift', 2, '<<=')
add_operator('inplace_rshift', 2, '>>=')
add_operator('inplace_and', 2, '&=')
add_operator('inplace_or', 2, '|=')
add_operator('inplace_xor', 2, '^=')
add_operator('lt', 2, '<')
add_operator('le', 2, '<=')
add_operator('eq', 2, '==')
add_operator('ne', 2, '!=')
add_operator('gt', 2, '>')
add_operator('ge', 2, '>=')
add_operator('cmp', 2, 'cmp')   # rich cmps preferred
add_operator('coerce', 2, 'coerce')
add_operator('contains', 2, 'contains')
add_operator('iter', 1, 'iter')
add_operator('next', 1, 'next')
#add_operator('call', 3, 'call')
add_operator('get', 3, 'get')
add_operator('set', 3, 'set')
add_operator('delete', 2, 'delete')
add_operator('userdel', 1, 'del')
add_operator('buffer', 1, 'buffer')   # see buffer.py


FunctionByName = {}   # dict {"operation_name": <built-in function>}
OperationName  = {}   # dict {<built-in function>: "operation_name"}
Arity          = {}   # dict {"operation name": number of arguments}

# ____________________________________________________________

def new_style_type(x):
    """Simulate a situation where every class is new-style"""
    return getattr(x, '__class__', type(x))

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

def lshift_ovf(x, y):
    return ovfcheck(x << y)

# slicing: operator.{get,set,del}slice() don't support b=None or c=None
def do_getslice(a, b, c):
    return a[b:c]

def do_setslice(a, b, c, d):
    a[b:c] = d

def do_delslice(a, b, c):
    del a[b:c]

def unsupported(*args):
    raise ValueError("this is not supported")

# ____________________________________________________________

# The following table can list several times the same operation name,
# if multiple built-in functions correspond to it.  The first one should
# be picked, though, as the best built-in for the given operation name.
# Lines ('name', operator.name) are added automatically.

# INTERNAL ONLY, use the dicts declared at the top of the file.
Table = [
    ('id',              id),
    ('type',            new_style_type),
    ('isinstance',      isinstance),
    ('issubtype',       issubclass),
    ('repr',            repr),
    ('str',             str),
    ('format',          unsupported),
    ('len',             len),
    ('hash',            hash),
    ('getattr',         getattr),
    ('setattr',         setattr),
    ('delattr',         delattr),
    ('nonzero',         bool),
    ('is_true',         bool),
    ('trunc',           unsupported),
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
    ('getslice',        do_getslice),
    ('setslice',        do_setslice),
    ('delslice',        do_delslice),
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

# build the dictionaries
for name, func in Table:
    if name not in FunctionByName:
        FunctionByName[name] = func
    if func not in OperationName:
        OperationName[func] = name
del Table  # INTERNAL ONLY, use the dicts declared at the top of the file

# insert all operators
for name in vars(op):
    if hasattr(operator, name):
        func = getattr(operator, name)
        if name not in FunctionByName:
            FunctionByName[name] = func
        if func not in OperationName:
            OperationName[func] = name

# Other functions that get directly translated to SpaceOperators
func2op = {type: op.type, operator.truth: op.nonzero}
if hasattr(__builtin__, 'next'):
    func2op[__builtin__.next] = op.next
for func, oper in func2op.iteritems():
    OperationName[func] = oper.name


op_appendices = {
    OverflowError: 'ovf',
    IndexError: 'idx',
    KeyError: 'key',
    ZeroDivisionError: 'zer',
    ValueError: 'val',
    }

implicit_exceptions = {
    int: [ValueError],      # built-ins that can always raise exceptions
    float: [ValueError],
    chr: [ValueError],
    unichr: [ValueError],
    unicode: [UnicodeDecodeError],
    # specifying IndexError, and KeyError beyond Exception,
    # allows the annotator to be more precise, see test_reraiseAnything/KeyError in
    # the annotator tests
    'getitem': [IndexError, KeyError, Exception],
    'setitem': [IndexError, KeyError, Exception],
    'delitem': [IndexError, KeyError, Exception],
    'contains': [Exception],    # from an r_dict
    }

def _add_exceptions(names, exc):
    for name in names.split():
        lis = implicit_exceptions.setdefault(name, [])
        if exc in lis:
            raise ValueError, "your list is causing duplication!"
        lis.append(exc)
        assert exc in op_appendices

def _add_except_ovf(names):
    # duplicate exceptions and add OverflowError
    for name in names.split():
        lis = implicit_exceptions.setdefault(name, [])[:]
        lis.append(OverflowError)
        implicit_exceptions[name+"_ovf"] = lis

_add_exceptions("""div mod divmod truediv floordiv pow
                   inplace_div inplace_mod inplace_divmod inplace_truediv
                   inplace_floordiv inplace_pow""", ZeroDivisionError)
_add_exceptions("""pow inplace_pow lshift inplace_lshift rshift
                   inplace_rshift""", ValueError)
_add_exceptions("""truediv divmod
                   inplace_add inplace_sub inplace_mul inplace_truediv
                   inplace_floordiv inplace_div inplace_mod inplace_pow
                   inplace_lshift""", OverflowError) # without a _ovf version
_add_except_ovf("""neg abs add sub mul
                   floordiv div mod pow lshift""")   # with a _ovf version
_add_exceptions("""pow""",
                OverflowError) # for the float case
del _add_exceptions, _add_except_ovf
