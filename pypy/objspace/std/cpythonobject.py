"""
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter.function import Function
from stringobject import W_StringObject
from intobject import W_IntObject
import sys, operator, types

class W_BuiltinFunctionObject(Function):
    """This class wraps cpython-functions much like ordinary 'Function' objects 
       but it avoids wrapping them into CPythonObject which would go badly 
       with the descroperations. """ 

    def __init__(self, space, cpyfunc):
        assert callable(cpyfunc), cpyfunc
        self.space = space
        self.cpyfunc = cpyfunc

    def call(self, w_args, w_kwds):
        space = self.space
        args = space.unwrap(w_args)
        kwds = {}
        keys_w = space.unpackiterable(w_kwds)
        for w_key in keys_w:
            kwds[space.unwrap(w_key)] = space.unwrap(space.getitem(w_kwds, w_key))
        try:
            result = apply(self.cpyfunc, args, kwds)
        except:
            wrap_exception(space)
        return space.wrap(result)

class W_CPythonObject(W_Object):
    "This class wraps an arbitrary CPython object."
    
    def __init__(w_self, space, cpyobj):
        W_Object.__init__(w_self, space)
        w_self.cpyobj = cpyobj

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "cpyobj(%r)" % (w_self.cpyobj,)

registerimplementation(W_CPythonObject)


def cpython_unwrap(space, w_obj):
    cpyobj = w_obj.cpyobj
    if hasattr(type(cpyobj), '__unwrap__'):
        cpyobj = cpyobj.__unwrap__()
    return cpyobj

StdObjSpace.unwrap.register(cpython_unwrap, W_CPythonObject)

# XXX we hack a bit to delegate ints to longs here
def hacky_delegate_to_long(space, w_intobj):
    return space.wrap(long(w_intobj.intval))
hacky_delegate_to_long.result_class = W_CPythonObject  # XXX
hacky_delegate_to_long.priority = PRIORITY_CHANGE_TYPE + 0.1  # XXX too
StdObjSpace.delegate.register(hacky_delegate_to_long, W_IntObject)


# XXX XXX XXX
# std space lookup now *refers directly* to the cpython descriptors
# so the multimethods implementations here are not reachable
# nor used, except for things implemented as multimethod directly on the space
# not through descriptors in DescrOperation
#
# delegate
# id
# issubtype
# ord
# round
# unwrap
#
# TODO kill



# real-to-wrapped exceptions
def wrap_exception(space):
    exc, value, tb = sys.exc_info()
    if exc is OperationError:
        raise exc, value, tb   # just re-raise it
    name = exc.__name__
    if hasattr(space, 'w_' + name):
        w_exc = getattr(space, 'w_' + name)
    else:
        w_exc = space.wrap(exc)
    raise OperationError, OperationError(w_exc, space.wrap(value)), tb

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

def getter(o, i, c):
    if hasattr(o, '__get__'):
        return o.__get__(i, c)
    else:
        return o

# regular part of the interface (minus 'next' and 'call')
MethodImplementation = {
    'id':                 id,
    'type':               type,
#    'issubtype':          see below,
    'repr':               repr,
    'str':                str,
    'len':                len,
    'hash':               hash,
    'getattr':            getattr,
    'setattr':            setattr,
    'delattr':            delattr,
#    'getitem':            see below,
#    'setitem':            see below,
#    'delitem':            see below,
    'pos':                operator.pos,
    'neg':                operator.neg,
    'abs':                operator.abs,
    'hex':                hex,
    'oct':                oct,
    'ord':                ord,
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
    'int':                int,
    'float':              float,
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
    'get':                getter,
#    'set':                setter,
#    'delete':             deleter,
    }

for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    f = MethodImplementation.get(_name)
    if f:
        if _arity == 1:
            def cpython_f(space, w_1, f=f): 
                x1 = w_1.cpyobj 
                type_x1 = type(x1)
                try:
                    y = f(x1)
                except:
                    wrap_exception(space)
                return space.wrap(y)
        elif _arity == 2:
            def cpython_f(space, w_1, w_2, f=f): 
                x1 = w_1.cpyobj 
                type_x1 = type(x1)
                # XXX do we really want to unwrap unknown objects here? 
                x2 = space.unwrap(w_2)
                try:
                    y = f(x1, x2)
                except:
                    wrap_exception(space)
                return space.wrap(y)
        elif _arity == 3:
            def cpython_f(space, w_1, w_2, w_3, f=f): 
                x1 = w_1.cpyobj 
                type_x1 = type(x1)
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
        #if _name == 'getattr': _name = 'getattribute'  # XXX hack
        multimethod = getattr(StdObjSpace.MM, _name)
        multimethod.register(cpython_f, *arglist)

        if len(multimethod.specialnames) > 1 and _arity == 2:
            def cpython_f_rev(space, w_1, w_2, f=f):
                # XXX do we really want to unwrap unknown objects here? 
                x1 = space.unwrap(w_1)
                x2 = w_2.cpyobj 
                try:
                    y = f(x1, x2)
                except:
                    wrap_exception(space)
                return space.wrap(y)
            multimethod.register(cpython_f_rev, W_ANY, W_CPythonObject)

def nonzero__CPython(space, w_obj):
    obj = space.unwrap(w_obj)
    try:
        return space.newbool(operator.truth(obj))
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

def getitem__CPython_ANY(space, w_obj, w_index):
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

def setitem__CPython_ANY_ANY(space, w_obj, w_index, w_value):
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

def delitem__CPython_ANY(space, w_obj, w_index):
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

def next__CPython(space, w_obj):
    obj = space.unwrap(w_obj)
    try:
        result = obj.next()
    except:
        wrap_exception(space)
    return space.wrap(result)

def call__CPython(space, w_obj, w_arguments, w_keywords):
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

def issubtype__CPython_ANY(space, w_obj, w_other):
    return space.newbool(0)

def issubtype__ANY_CPython(space, w_obj, w_other):
    return space.newbool(0)

def issubtype__CPython_CPython(space, w_obj, w_other):
    return space.newbool(issubclass(space.unwrap(w_obj),
                                    space.unwrap(w_other)))

register_all(vars())
