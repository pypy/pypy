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

func2op = {}

class SpaceOperator(object):
    def __init__(self, name, arity, symbol, pyfunc):
        self.name = name
        self.arity = arity
        self.symbol = symbol
        self.pyfunc = pyfunc

def add_operator(name, arity, symbol, pyfunc=None):
    operator_func = getattr(operator, name, None)
    oper = SpaceOperator(name, arity, symbol, pyfunc)
    setattr(op, name, oper)
    if pyfunc is not None:
        func2op[pyfunc] = oper
    if operator_func:
        func2op[operator_func] = oper
        if pyfunc is None:
            oper.pyfunc = operator_func

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


add_operator('is_', 2, 'is')
add_operator('id', 1, 'id', pyfunc=id)
add_operator('type', 1, 'type', pyfunc=new_style_type)
add_operator('isinstance', 2, 'isinstance', pyfunc=isinstance)
add_operator('issubtype', 2, 'issubtype', pyfunc=issubclass)  # not for old-style classes
add_operator('repr', 1, 'repr', pyfunc=repr)
add_operator('str', 1, 'str', pyfunc=str)
add_operator('format', 2, 'format', pyfunc=unsupported)
add_operator('len', 1, 'len', pyfunc=len)
add_operator('hash', 1, 'hash', pyfunc=hash)
add_operator('getattr', 2, 'getattr', pyfunc=getattr)
add_operator('setattr', 3, 'setattr', pyfunc=setattr)
add_operator('delattr', 2, 'delattr', pyfunc=delattr)
add_operator('getitem', 2, 'getitem')
add_operator('setitem', 3, 'setitem')
add_operator('delitem', 2, 'delitem')
add_operator('getslice', 3, 'getslice', pyfunc=do_getslice)
add_operator('setslice', 4, 'setslice', pyfunc=do_setslice)
add_operator('delslice', 3, 'delslice', pyfunc=do_delslice)
add_operator('trunc', 1, 'trunc', pyfunc=unsupported)
add_operator('pos', 1, 'pos')
add_operator('neg', 1, 'neg')
add_operator('nonzero', 1, 'truth', pyfunc=bool)
op.is_true = op.nonzero
add_operator('abs' , 1, 'abs', pyfunc=abs)
add_operator('hex', 1, 'hex', pyfunc=hex)
add_operator('oct', 1, 'oct', pyfunc=oct)
add_operator('ord', 1, 'ord', pyfunc=ord)
add_operator('invert', 1, '~')
add_operator('add', 2, '+')
add_operator('sub', 2, '-')
add_operator('mul', 2, '*')
add_operator('truediv', 2, '/')
add_operator('floordiv', 2, '//')
add_operator('div', 2, 'div')
add_operator('mod', 2, '%')
add_operator('divmod', 2, 'divmod', pyfunc=divmod)
add_operator('pow', 3, '**', pyfunc=pow)
add_operator('lshift', 2, '<<')
add_operator('rshift', 2, '>>')
add_operator('and_', 2, '&')
add_operator('or_', 2, '|')
add_operator('xor', 2, '^')
add_operator('int', 1, 'int', pyfunc=do_int)
add_operator('index', 1, 'index', pyfunc=do_index)
add_operator('float', 1, 'float', pyfunc=do_float)
add_operator('long', 1, 'long', pyfunc=do_long)
add_operator('inplace_add', 2, '+=', pyfunc=inplace_add)
add_operator('inplace_sub', 2, '-=', pyfunc=inplace_sub)
add_operator('inplace_mul', 2, '*=', pyfunc=inplace_mul)
add_operator('inplace_truediv', 2, '/=', pyfunc=inplace_truediv)
add_operator('inplace_floordiv', 2, '//=', pyfunc=inplace_floordiv)
add_operator('inplace_div', 2, 'div=', pyfunc=inplace_div)
add_operator('inplace_mod', 2, '%=', pyfunc=inplace_mod)
add_operator('inplace_pow', 2, '**=', pyfunc=inplace_pow)
add_operator('inplace_lshift', 2, '<<=', pyfunc=inplace_lshift)
add_operator('inplace_rshift', 2, '>>=', pyfunc=inplace_rshift)
add_operator('inplace_and', 2, '&=', pyfunc=inplace_and)
add_operator('inplace_or', 2, '|=', pyfunc=inplace_or)
add_operator('inplace_xor', 2, '^=', pyfunc=inplace_xor)
add_operator('lt', 2, '<')
add_operator('le', 2, '<=')
add_operator('eq', 2, '==')
add_operator('ne', 2, '!=')
add_operator('gt', 2, '>')
add_operator('ge', 2, '>=')
add_operator('cmp', 2, 'cmp', pyfunc=cmp)   # rich cmps preferred
add_operator('coerce', 2, 'coerce', pyfunc=coerce)
add_operator('contains', 2, 'contains')
add_operator('iter', 1, 'iter', pyfunc=iter)
add_operator('next', 1, 'next', pyfunc=next)
#add_operator('call', 3, 'call')
add_operator('get', 3, 'get', pyfunc=get)
add_operator('set', 3, 'set', pyfunc=set)
add_operator('delete', 2, 'delete', pyfunc=delete)
add_operator('userdel', 1, 'del', pyfunc=userdel)
add_operator('buffer', 1, 'buffer', pyfunc=buffer)   # see buffer.py

# --- operations added by graph transformations ---
for oper in [op.neg, op.abs, op.add, op.sub, op.mul, op.floordiv, op.div,
        op.mod, op.lshift]:
    ovf_func = lambda *args: ovfcheck(oper.pyfunc(*args))
    add_operator(oper.name + '_ovf', oper.arity, oper.symbol, pyfunc=ovf_func)

# Other functions that get directly translated to SpaceOperators
func2op[type] = op.type
func2op[operator.truth] = op.nonzero
if hasattr(__builtin__, 'next'):
    func2op[__builtin__.next] = op.next


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
