from pypy.objspace.std.objspace import *
from stringobject import W_StringObject
import sys, operator, types

class W_CPythonObject(W_Object):
    "This class wraps an arbitrary CPython object."

    delegate_once = {}
    
    def __init__(w_self, space, cpyobj):
        W_Object.__init__(w_self, space)
        w_self.cpyobj = cpyobj

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "wrap(%r)" % (w_self.cpyobj,)


def cpython_unwrap(space, w_obj):
    return w_obj.cpyobj

StdObjSpace.unwrap.register(cpython_unwrap, W_CPythonObject)


# real-to-wrapped exceptions
def wrap_exception(space):
    exc, value, tb = sys.exc_info()
    raise OperationError(space.wrap(exc), space.wrap(value))

# in-place operators
def inplace_pow(x1, x2):
    x1 **= x2
    return x1
def inplace_mul(x1, x2):
    x1 *= x2
    return x1
def inplace_truediv(x1, x2):
    x1 /= x2  # XXX depends on compiler flags
    return x1
def inplace_floordiv(x1, x2):
    x1 //= x2
    return x1
def inplace_div(x1, x2):
    x1 /= x2  # XXX depends on compiler flags
    return x1
def inplace_mod(x1, x2):
    x1 %= x2
    return x1

def inplace_add(x1, x2):
    x1 += x2
    return x1
def inplace_sub(x1, x2):
    x1 -= x2
    return x1
def inplace_lshift(x1, x2):
    x1 <<= x2
    return x1
def inplace_rshift(x1, x2):
    x1 >>= x2
    return x1
def inplace_and(x1, x2):
    x1 &= x2
    return x1
def inplace_or(x1, x2):
    x1 |= x2
    return x1
def inplace_xor(x1, x2):
    x1 ^= x2
    return x1

# regular part of the interface (minus 'next' and 'call')
MethodImplementation = {
    'id':                 id,
    'type':               type,
    'issubtype':          issubclass,
    'repr':               repr,
    'str':                str,
    'len':                len,
    'hash':               hash,
    'getattr':            getattr,
    'setattr':            setattr,
    'delattr':            delattr,
    'pos':                operator.pos,
    'neg':                operator.neg,
    'not_':               operator.not_,
    'abs':                operator.abs,
    'invert':             operator.invert,
    'add':                operator.add,
    'sub':                operator.sub,
    'mul':                operator.mul,
    'truediv':            operator.truediv,
    'floordiv':           operator.floordiv,
    'div':                operator.div,
    'mod':                operator.mod,
    'divmod':             divmod,
    'pow':                pow,
    'lshift':             operator.lshift,
    'rshift':             operator.rshift,
    'and_':               operator.and_,
    'or_':                operator.or_,
    'xor':                operator.xor,
    'inplace_add':        inplace_add,
    'inplace_sub':        inplace_sub,
    'inplace_mul':        inplace_mul,
    'inplace_truediv':    inplace_truediv,
    'inplace_floordiv':   inplace_floordiv,
    'inplace_div':        inplace_div,
    'inplace_mod':        inplace_mod,
    'inplace_pow':        inplace_pow,
    'inplace_lshift':     inplace_lshift,
    'inplace_rshift':     inplace_rshift,
    'inplace_and':        inplace_and,
    'inplace_or':         inplace_or,
    'inplace_xor':        inplace_xor,
    'lt':                 operator.lt,
    'le':                 operator.le,
    'eq':                 operator.eq,
    'ne':                 operator.ne,
    'gt':                 operator.gt,
    'ge':                 operator.ge,
    'contains':           operator.contains,
    'iter':               iter,
    }

for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    f = MethodImplementation.get(_name)
    if f:
        if _arity == 1:
            def cpython_f(space, w_1, f=f):
                x = space.unwrap(w_1)
                try:
                    y = f(x)
                except:
                    wrap_exception(space)
                return space.wrap(y)
        elif _arity == 2:
            def cpython_f(space, w_1, w_2, f=f):
                x1 = space.unwrap(w_1)
                x2 = space.unwrap(w_2)
                try:
                    y = f(x1, x2)
                except:
                    wrap_exception(space)
                return space.wrap(y)
        elif _arity == 3:
            def cpython_f(space, w_1, w_2, w_3, f=f):
                x1 = space.unwrap(w_1)
                x2 = space.unwrap(w_2)
                x3 = space.unwrap(w_3)
                try:
                    y = f(x1, x2, x3)
                except:
                    wrap_exception(space)
                return space.wrap(y)
        else:
            raise ValueError, '_arity too large'

        arglist = [W_CPythonObject] + [W_ANY]*(_arity-1)
        multimethod = getattr(StdObjSpace, _name)
        multimethod.register(cpython_f, *arglist)


def cpython_is_true(space, w_obj):
    obj = space.unwrap(w_obj)
    try:
        return operator.truth(obj)
    except:
        wrap_exception(space)


# slicing
def old_slice(index):
    # return the (start, stop) indices of the slice, or None
    # if the w_index is not a slice or a slice with a step
    # this is no longer useful in Python 2.3
    if isinstance(index, types.SliceType):
        if index.step is None or index.step == 1:
            start, stop = index.start, index.stop
            if start is None: start = 0
            if stop  is None: stop  = sys.maxint
            return start, stop
    return None

def cpython_getitem(space, w_obj, w_index):
    obj = space.unwrap(w_obj)
    index = space.unwrap(w_index)
    sindex = old_slice(index)
    try:
        if sindex is None:
            result = obj[index]
        else:
            result = operator.getslice(obj, sindex[0], sindex[1])
    except:
        wrap_exception(space)
    return space.wrap(result)

def cpython_setitem(space, w_obj, w_index, w_value):
    obj = space.unwrap(w_obj)
    index = space.unwrap(w_index)
    value = space.unwrap(w_value)
    sindex = old_slice(index)
    try:
        if sindex is None:
            obj[index] = value
        else:
            operator.setslice(obj, sindex[0], sindex[1], value)
    except:
        wrap_exception(space)

def cpython_delitem(space, w_obj, w_index):
    obj = space.unwrap(w_obj)
    index = space.unwrap(w_index)
    sindex = old_slice(index)
    try:
        if sindex is None:
            del obj[index]
        else:
            operator.delslice(obj, sindex[0], sindex[1])
    except:
        wrap_exception(space)

StdObjSpace.getitem.register(cpython_getitem, W_CPythonObject, W_ANY)
StdObjSpace.setitem.register(cpython_getitem, W_CPythonObject, W_ANY, W_ANY)
StdObjSpace.delitem.register(cpython_getitem, W_CPythonObject, W_ANY)


def cpython_next(space, w_obj):
    obj = space.unwrap(w_obj)
    try:
        result = obj.next()
    except StopIteration:
        raise NoValue
    except:
        wrap_exception(space)
    return space.wrap(result)

StdObjSpace.next.register(cpython_next, W_CPythonObject)


def cpython_call(space, w_obj, w_arguments, w_keywords):
    # XXX temporary hack similar to objspace.trivial.call()
    callable = space.unwrap(w_obj)
    args = space.unwrap(w_arguments)
    keywords = space.unwrap(w_keywords)
    try:
        result = apply(callable, args, keywords)
    except:
        import sys
        wrap_exception(space)
    return space.wrap(result)

StdObjSpace.call.register(cpython_call, W_CPythonObject, W_ANY, W_ANY)
