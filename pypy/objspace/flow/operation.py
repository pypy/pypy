"""
This module defines mappings between operation names and Python's
built-in functions (or type constructors) implementing them.
"""

import __builtin__
import __future__
import operator
import types
import sys
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.error import OperationError
from pypy.tool.sourcetools import compile2
from pypy.rlib.rarithmetic import ovfcheck, ovfcheck_lshift
from pypy.objspace.flow import model


class OperationThatShouldNotBePropagatedError(OperationError):
    pass

class ImplicitOperationError(OperationError):
    pass


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

def setup():
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
del Table, setup # INTERNAL ONLY, use the dicts declared at the top of the file

op_appendices = {
    OverflowError: 'ovf',
    IndexError: 'idx',
    KeyError: 'key',
    AttributeError: 'att',
    TypeError: 'typ',
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

for _name in 'getattr', 'delattr':
    _add_exceptions(_name, AttributeError)
for _name in 'iter', 'coerce':
    _add_exceptions(_name, TypeError)
del _name

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

def make_op(fs, name, symbol, arity, specialnames):
    if hasattr(fs, name):
        return

    op = None
    skip = False
    arithmetic = False

    if (name.startswith('del') or
        name.startswith('set') or
        name.startswith('inplace_')):
        # skip potential mutators
        skip = True
    elif name in ('id', 'hash', 'iter', 'userdel'):
        # skip potential runtime context dependecies
        skip = True
    elif name in ('repr', 'str'):
        rep = getattr(__builtin__, name)
        def op(obj):
            s = rep(obj)
            if "at 0x" in s:
                print >>sys.stderr, "Warning: captured address may be awkward"
            return s
    else:
        op = FunctionByName[name]
        arithmetic = (name + '_ovf') in FunctionByName

    if not op and not skip:
        raise ValueError("XXX missing operator: %s" % (name,))

    def generic_operator(self, *args_w):
        assert len(args_w) == arity, name + " got the wrong number of arguments"
        if op:
            args = []
            for w_arg in args_w:
                try:
                    arg = self.unwrap_for_computation(w_arg)
                except model.UnwrapException:
                    break
                else:
                    args.append(arg)
            else:
                # All arguments are constants: call the operator now
                try:
                    result = op(*args)
                except:
                    etype, evalue, etb = sys.exc_info()
                    msg = "generated by a constant operation:  %s%r" % (
                        name, tuple(args))
                    raise OperationThatShouldNotBePropagatedError(
                        self.wrap(etype), self.wrap(msg))
                else:
                    # don't try to constant-fold operations giving a 'long'
                    # result.  The result is probably meant to be sent to
                    # an intmask(), but the 'long' constant confuses the
                    # annotator a lot.
                    if arithmetic and type(result) is long:
                        pass
                    # don't constant-fold getslice on lists, either
                    elif name == 'getslice' and type(result) is list:
                        pass
                    # otherwise, fine
                    else:
                        try:
                            return self.wrap(result)
                        except model.WrapException:
                            # type cannot sanely appear in flow graph,
                            # store operation with variable result instead
                            pass
        w_result = self.do_operation_with_implicit_exceptions(name, *args_w)
        return w_result

    setattr(fs, name, generic_operator)


"""
This is just a placeholder for some code I'm checking in elsewhere.
It is provenly possible to determine constantness of certain expressions
a little later. I introduced this a bit too early, together with tieing
this to something being global, which was a bad idea.
The concept is still valid, and it can  be used to force something to
be evaluated immediately because it is supposed to be a constant.
One good possible use of this is loop unrolling.
This will be found in an 'experimental' folder with some use cases.
"""

def special_overrides(fs):
    def getattr(self, w_obj, w_name):
        # handling special things like sys
        # unfortunately this will never vanish with a unique import logic :-(
        if w_obj in self.not_really_const:
            const_w = self.not_really_const[w_obj]
            if w_name not in const_w:
                return self.do_operation_with_implicit_exceptions('getattr',
                                                                  w_obj, w_name)
        return self.regular_getattr(w_obj, w_name)

    fs.regular_getattr = fs.getattr
    fs.getattr = getattr

    # protect us from globals write access
    def setitem(self, w_obj, w_key, w_val):
        ec = self.getexecutioncontext()
        if not (ec and w_obj is ec.w_globals):
            return self.regular_setitem(w_obj, w_key, w_val)
        raise SyntaxError("attempt to modify global attribute %r in %r"
                          % (w_key, ec.graph.func))

    fs.regular_setitem = fs.setitem
    fs.setitem = setitem


def add_operations(fs):
    """Add function operations to the flow space."""
    for line in ObjSpace.MethodTable:
        make_op(fs, *line)
    special_overrides(fs)
