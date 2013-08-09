"""
This module defines mappings between operation names and Python's
built-in functions (or type constructors) implementing them.
"""

import __builtin__
import __future__
import operator
from rpython.tool.sourcetools import compile2
from rpython.flowspace.model import Constant, WrapException, const
from rpython.flowspace.specialcase import register_flow_sc

class _OpHolder(object): pass
op = _OpHolder()

func2op = {}

class SpaceOperator(object):
    pure = False
    def __init__(self, name, arity, symbol, pyfunc, can_overflow=False):
        self.name = name
        self.arity = arity
        self.symbol = symbol
        self.pyfunc = pyfunc
        self.can_overflow = can_overflow
        self.canraise = []

    def make_sc(self):
        def sc_operator(space, args_w):
            if len(args_w) != self.arity:
                if self is op.pow and len(args_w) == 2:
                    args_w = args_w + [Constant(None)]
                elif self is op.getattr and len(args_w) == 3:
                    return space.frame.do_operation('simple_call', Constant(getattr), *args_w)
                else:
                    raise Exception("should call %r with exactly %d arguments" % (
                        self.name, self.arity))
            # completely replace the call with the underlying
            # operation and its limited implicit exceptions semantic
            return getattr(space, self.name)(*args_w)
        return sc_operator

    def eval(self, frame, *args_w):
        if len(args_w) != self.arity:
            raise TypeError(self.name + " got the wrong number of arguments")
        return frame.do_op(self, *args_w)

class PureOperator(SpaceOperator):
    pure = True

    def eval(self, frame, *args_w):
        if len(args_w) != self.arity:
            raise TypeError(self.name + " got the wrong number of arguments")
        args = []
        if all(w_arg.foldable() for w_arg in args_w):
            args = [w_arg.value for w_arg in args_w]
            # All arguments are constants: call the operator now
            try:
                result = self.pyfunc(*args)
            except Exception as e:
                from rpython.flowspace.flowcontext import FlowingError
                msg = "%s%r always raises %s: %s" % (
                    self.name, tuple(args), type(e), e)
                raise FlowingError(frame, msg)
            else:
                # don't try to constant-fold operations giving a 'long'
                # result.  The result is probably meant to be sent to
                # an intmask(), but the 'long' constant confuses the
                # annotator a lot.
                if self.can_overflow and type(result) is long:
                    pass
                # don't constant-fold getslice on lists, either
                elif self.name == 'getslice' and type(result) is list:
                    pass
                # otherwise, fine
                else:
                    try:
                        return const(result)
                    except WrapException:
                        # type cannot sanely appear in flow graph,
                        # store operation with variable result instead
                        pass
        return frame.do_op(self, *args_w)


def add_operator(name, arity, symbol, pyfunc=None, pure=False, ovf=False):
    operator_func = getattr(operator, name, None)
    cls = PureOperator if pure else SpaceOperator
    oper = cls(name, arity, symbol, pyfunc, can_overflow=ovf)
    setattr(op, name, oper)
    if pyfunc is not None:
        func2op[pyfunc] = oper
    if operator_func:
        func2op[operator_func] = oper
        if pyfunc is None:
            oper.pyfunc = operator_func
    if ovf:
        from rpython.rlib.rarithmetic import ovfcheck
        ovf_func = lambda *args: ovfcheck(oper.pyfunc(*args))
        add_operator(name + '_ovf', arity, symbol, pyfunc=ovf_func)

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

# slicing: operator.{get,set,del}slice() don't support b=None or c=None
def do_getslice(a, b, c):
    return a[b:c]

def do_setslice(a, b, c, d):
    a[b:c] = d

def do_delslice(a, b, c):
    del a[b:c]

def unsupported(*args):
    raise ValueError("this is not supported")


add_operator('is_', 2, 'is', pure=True)
add_operator('id', 1, 'id', pyfunc=id)
add_operator('type', 1, 'type', pyfunc=new_style_type, pure=True)
add_operator('isinstance', 2, 'isinstance', pyfunc=isinstance, pure=True)
add_operator('issubtype', 2, 'issubtype', pyfunc=issubclass, pure=True)  # not for old-style classes
add_operator('repr', 1, 'repr', pyfunc=repr, pure=True)
add_operator('str', 1, 'str', pyfunc=str, pure=True)
add_operator('format', 2, 'format', pyfunc=unsupported)
add_operator('len', 1, 'len', pyfunc=len, pure=True)
add_operator('hash', 1, 'hash', pyfunc=hash)
add_operator('getattr', 2, 'getattr', pyfunc=getattr, pure=True)
add_operator('setattr', 3, 'setattr', pyfunc=setattr)
add_operator('delattr', 2, 'delattr', pyfunc=delattr)
add_operator('getitem', 2, 'getitem', pure=True)
add_operator('setitem', 3, 'setitem')
add_operator('delitem', 2, 'delitem')
add_operator('getslice', 3, 'getslice', pyfunc=do_getslice, pure=True)
add_operator('setslice', 4, 'setslice', pyfunc=do_setslice)
add_operator('delslice', 3, 'delslice', pyfunc=do_delslice)
add_operator('trunc', 1, 'trunc', pyfunc=unsupported)
add_operator('pos', 1, 'pos', pure=True)
add_operator('neg', 1, 'neg', pure=True, ovf=True)
add_operator('nonzero', 1, 'truth', pyfunc=bool, pure=True)
op.is_true = op.nonzero
add_operator('abs' , 1, 'abs', pyfunc=abs, pure=True, ovf=True)
add_operator('hex', 1, 'hex', pyfunc=hex, pure=True)
add_operator('oct', 1, 'oct', pyfunc=oct, pure=True)
add_operator('ord', 1, 'ord', pyfunc=ord, pure=True)
add_operator('invert', 1, '~', pure=True)
add_operator('add', 2, '+', pure=True, ovf=True)
add_operator('sub', 2, '-', pure=True, ovf=True)
add_operator('mul', 2, '*', pure=True, ovf=True)
add_operator('truediv', 2, '/', pure=True)
add_operator('floordiv', 2, '//', pure=True, ovf=True)
add_operator('div', 2, 'div', pure=True, ovf=True)
add_operator('mod', 2, '%', pure=True, ovf=True)
add_operator('divmod', 2, 'divmod', pyfunc=divmod, pure=True)
add_operator('pow', 3, '**', pyfunc=pow, pure=True)
add_operator('lshift', 2, '<<', pure=True, ovf=True)
add_operator('rshift', 2, '>>', pure=True)
add_operator('and_', 2, '&', pure=True)
add_operator('or_', 2, '|', pure=True)
add_operator('xor', 2, '^', pure=True)
add_operator('int', 1, 'int', pyfunc=do_int, pure=True)
add_operator('index', 1, 'index', pyfunc=do_index, pure=True)
add_operator('float', 1, 'float', pyfunc=do_float, pure=True)
add_operator('long', 1, 'long', pyfunc=do_long, pure=True)
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
add_operator('lt', 2, '<', pure=True)
add_operator('le', 2, '<=', pure=True)
add_operator('eq', 2, '==', pure=True)
add_operator('ne', 2, '!=', pure=True)
add_operator('gt', 2, '>', pure=True)
add_operator('ge', 2, '>=', pure=True)
add_operator('cmp', 2, 'cmp', pyfunc=cmp, pure=True)   # rich cmps preferred
add_operator('coerce', 2, 'coerce', pyfunc=coerce, pure=True)
add_operator('contains', 2, 'contains', pure=True)
add_operator('iter', 1, 'iter', pyfunc=iter)
add_operator('next', 1, 'next', pyfunc=next)
#add_operator('call', 3, 'call')
add_operator('get', 3, 'get', pyfunc=get, pure=True)
add_operator('set', 3, 'set', pyfunc=set)
add_operator('delete', 2, 'delete', pyfunc=delete)
add_operator('userdel', 1, 'del', pyfunc=userdel)
add_operator('buffer', 1, 'buffer', pyfunc=buffer, pure=True)   # see buffer.py

# Other functions that get directly translated to SpaceOperators
func2op[type] = op.type
func2op[operator.truth] = op.nonzero
if hasattr(__builtin__, 'next'):
    func2op[__builtin__.next] = op.next

for fn, oper in func2op.items():
    register_flow_sc(fn)(oper.make_sc())


op_appendices = {
    OverflowError: 'ovf',
    IndexError: 'idx',
    KeyError: 'key',
    ZeroDivisionError: 'zer',
    ValueError: 'val',
    }

# specifying IndexError, and KeyError beyond Exception,
# allows the annotator to be more precise, see test_reraiseAnything/KeyError in
# the annotator tests
op.getitem.canraise = [IndexError, KeyError, Exception]
op.setitem.canraise = [IndexError, KeyError, Exception]
op.delitem.canraise = [IndexError, KeyError, Exception]
op.contains.canraise = [Exception]    # from an r_dict

def _add_exceptions(names, exc):
    for name in names.split():
        oper = getattr(op, name)
        lis = oper.canraise
        if exc in lis:
            raise ValueError, "your list is causing duplication!"
        lis.append(exc)
        assert exc in op_appendices

def _add_except_ovf(names):
    # duplicate exceptions and add OverflowError
    for name in names.split():
        oper = getattr(op, name)
        oper_ovf = getattr(op, name+'_ovf')
        oper_ovf.canraise = list(oper.canraise)
        oper_ovf.canraise.append(OverflowError)

_add_exceptions("""div mod divmod truediv floordiv pow
                   inplace_div inplace_mod inplace_truediv
                   inplace_floordiv inplace_pow""", ZeroDivisionError)
_add_exceptions("""pow inplace_pow lshift inplace_lshift rshift
                   inplace_rshift""", ValueError)
_add_exceptions("""truediv divmod
                   inplace_add inplace_sub inplace_mul inplace_truediv
                   inplace_floordiv inplace_div inplace_mod inplace_pow
                   inplace_lshift""", OverflowError) # without a _ovf version
_add_except_ovf("""neg abs add sub mul
                   floordiv div mod lshift""")   # with a _ovf version
_add_exceptions("""pow""",
                OverflowError) # for the float case
del _add_exceptions, _add_except_ovf
