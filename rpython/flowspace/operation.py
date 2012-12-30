"""
This module defines mappings between operation names and Python's
built-in functions (or type constructors) implementing them.
"""

import __builtin__
import __future__
import operator
from pypy.tool.sourcetools import compile2
from rpython.rlib.rarithmetic import ovfcheck

# this is a copy that should be shared with standard objspace

MethodTable = [
# method name # symbol # number of arguments # special method name(s)
    ('is_',             'is',        2, []),
    ('id',              'id',        1, []),
    ('type',            'type',      1, []),
    ('isinstance',      'isinstance', 2, ['__instancecheck__']),
    ('issubtype',       'issubtype', 2, ['__subclasscheck__']),  # not for old-style classes
    ('repr',            'repr',      1, ['__repr__']),
    ('str',             'str',       1, ['__str__']),
    ('format',          'format',    2, ['__format__']),
    ('len',             'len',       1, ['__len__']),
    ('hash',            'hash',      1, ['__hash__']),
    ('getattr',         'getattr',   2, ['__getattribute__']),
    ('setattr',         'setattr',   3, ['__setattr__']),
    ('delattr',         'delattr',   2, ['__delattr__']),
    ('getitem',         'getitem',   2, ['__getitem__']),
    ('setitem',         'setitem',   3, ['__setitem__']),
    ('delitem',         'delitem',   2, ['__delitem__']),
    ('getslice',        'getslice',  3, ['__getslice__']),
    ('setslice',        'setslice',  4, ['__setslice__']),
    ('delslice',        'delslice',  3, ['__delslice__']),
    ('trunc',           'trunc',     1, ['__trunc__']),
    ('pos',             'pos',       1, ['__pos__']),
    ('neg',             'neg',       1, ['__neg__']),
    ('nonzero',         'truth',     1, ['__nonzero__']),
    ('abs' ,            'abs',       1, ['__abs__']),
    ('hex',             'hex',       1, ['__hex__']),
    ('oct',             'oct',       1, ['__oct__']),
    ('ord',             'ord',       1, []),
    ('invert',          '~',         1, ['__invert__']),
    ('add',             '+',         2, ['__add__', '__radd__']),
    ('sub',             '-',         2, ['__sub__', '__rsub__']),
    ('mul',             '*',         2, ['__mul__', '__rmul__']),
    ('truediv',         '/',         2, ['__truediv__', '__rtruediv__']),
    ('floordiv',        '//',        2, ['__floordiv__', '__rfloordiv__']),
    ('div',             'div',       2, ['__div__', '__rdiv__']),
    ('mod',             '%',         2, ['__mod__', '__rmod__']),
    ('divmod',          'divmod',    2, ['__divmod__', '__rdivmod__']),
    ('pow',             '**',        3, ['__pow__', '__rpow__']),
    ('lshift',          '<<',        2, ['__lshift__', '__rlshift__']),
    ('rshift',          '>>',        2, ['__rshift__', '__rrshift__']),
    ('and_',            '&',         2, ['__and__', '__rand__']),
    ('or_',             '|',         2, ['__or__', '__ror__']),
    ('xor',             '^',         2, ['__xor__', '__rxor__']),
    ('int',             'int',       1, ['__int__']),
    ('index',           'index',     1, ['__index__']),
    ('float',           'float',     1, ['__float__']),
    ('long',            'long',      1, ['__long__']),
    ('inplace_add',     '+=',        2, ['__iadd__']),
    ('inplace_sub',     '-=',        2, ['__isub__']),
    ('inplace_mul',     '*=',        2, ['__imul__']),
    ('inplace_truediv', '/=',        2, ['__itruediv__']),
    ('inplace_floordiv','//=',       2, ['__ifloordiv__']),
    ('inplace_div',     'div=',      2, ['__idiv__']),
    ('inplace_mod',     '%=',        2, ['__imod__']),
    ('inplace_pow',     '**=',       2, ['__ipow__']),
    ('inplace_lshift',  '<<=',       2, ['__ilshift__']),
    ('inplace_rshift',  '>>=',       2, ['__irshift__']),
    ('inplace_and',     '&=',        2, ['__iand__']),
    ('inplace_or',      '|=',        2, ['__ior__']),
    ('inplace_xor',     '^=',        2, ['__ixor__']),
    ('lt',              '<',         2, ['__lt__', '__gt__']),
    ('le',              '<=',        2, ['__le__', '__ge__']),
    ('eq',              '==',        2, ['__eq__', '__eq__']),
    ('ne',              '!=',        2, ['__ne__', '__ne__']),
    ('gt',              '>',         2, ['__gt__', '__lt__']),
    ('ge',              '>=',        2, ['__ge__', '__le__']),
    ('cmp',             'cmp',       2, ['__cmp__']),   # rich cmps preferred
    ('coerce',          'coerce',    2, ['__coerce__', '__coerce__']),
    ('contains',        'contains',  2, ['__contains__']),
    ('iter',            'iter',      1, ['__iter__']),
    ('next',            'next',      1, ['next']),
#    ('call',            'call',      3, ['__call__']),
    ('get',             'get',       3, ['__get__']),
    ('set',             'set',       3, ['__set__']),
    ('delete',          'delete',    2, ['__delete__']),
    ('userdel',         'del',       1, ['__del__']),
    ('buffer',          'buffer',    1, ['__buffer__']),   # see buffer.py
    ]


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
    ('type',            type),
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
    ('nonzero',         operator.truth),
    ('is_true',         bool),
    ('is_true',         operator.truth),
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
if hasattr(__builtin__, 'next'):
    Table.append(('next', __builtin__.next))

def setup():
    # insert all operators
    for line in MethodTable:
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
    for line in MethodTable:
        name = line[0]
        Arity[name] = line[2]
        assert name in FunctionByName
setup()
del Table, setup # INTERNAL ONLY, use the dicts declared at the top of the file

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
