import operator
import pypy.lang.smalltalk.model as model
import pypy.lang.smalltalk.classtable as ct
import pypy.lang.smalltalk.fakeimage as fimg

class PrimitiveFailedError(Exception):
    pass

class PrimitiveNotYetWrittenError(PrimitiveFailedError):
    pass

def unwrap_int(w_v):
    if isinstance(w_v, model.W_SmallInteger): return w_v.value
    raise PrimitiveFailedError()

def unwrap_float(w_v):
    if isinstance(w_v, model.W_Float): return w_v.value
    elif isinstance(w_v, model.W_SmallInteger): return float(w_v.value)
    raise PrimitiveFailedError()

def is_valid_index(idx, w_obj):
    return idx >= 0 and idx < w_obj.size()

# ___________________________________________________________________________
# Primitive table: it is filled in at initialization time with the
# primitive functions.  Each primitive function takes a single argument,
# the frame (a W_ContextFrame object); the function either completes, and
# returns a result, or throws a PrimitiveFailedError.

prim_table = [None] * 127

def primitive(code):
    def decorator(func):
        prim_table[code] = func
        return func
    return decorator

def stack(n):
    def decorator(wrapped):
        def result(frame):
            items = [frame.peek(i) for i in range(n)]
            res = wrapped(items)
            frame.pop_n(n)   # only if no exception occurs!
            return res
        return result
    return decorator

# ___________________________________________________________________________
# Small Integer Primitives

ADD = 1
SUBTRACT = 2
MAKE_POINT = 18

math_ops = {
    ADD: operator.add,
    SUBTRACT: operator.sub
    }
for (code,op) in math_ops.items():
    @stack(2)
    def func(stack, op=op): # n.b. capture op value
        [w_v2, w_v1] = stack
        v1 = unwrap_int(w_v1)
        v2 = unwrap_int(w_v2)
        res = op(v1, v2)
        
        # Emulate the bounds of smalltalk tagged integers:
        if res > 1073741823: raise PrimitiveFailedError()
        if res < -1073741824: raise PrimitiveFailedError()
        
        w_res = fimg.small_int(res)
        return w_res
    prim_table[code] = func

@primitive(MAKE_POINT)
def primitivemakepoint(frame):
    raise PrimitiveNotYetWrittenError(MAKE_POINT)

# ___________________________________________________________________________
# Integer Primitives
#
# Primitives 21-37 are aliased to 1-17 for historical reasons.

for i in range(21,38):
    prim_table[i] = prim_table[i-20]

# ___________________________________________________________________________
# Float Primitives

_FLOAT_OFFSET = 40
FLOAT_ADD = 41
FLOAT_SUBTRACT = 42
math_ops = {
    FLOAT_ADD: operator.add,
    FLOAT_SUBTRACT: operator.sub
    }
for (code,op) in math_ops.items():
    @stack(2)
    def func(res, op=op): # n.b. capture op value
        [w_v2, w_v1] = res
        v1 = unwrap_float(w_v1)
        v2 = unwrap_float(w_v2)
        w_res = fimg.wrap_float(op(v1, v2))
        return w_res
    prim_table[code] = func

# ___________________________________________________________________________
# Subscript and Stream Primitives

AT = 60
AT_PUT = 61
SIZE = 62
STRING_AT = 63
STRING_AT_PUT = 64
OBJECT_AT = 68
OBJECT_AT_PUT = 69

def common_at(stack):
    [w_idx, w_obj] = stack
    idx = unwrap_int(w_idx)
    if not is_valid_index(idx, w_obj):
        raise PrimitiveFailedError()
    return idx, w_obj

def common_at_put(stack):
    [w_val, w_idx, w_obj] = stack
    idx = unwrap_int(w_idx)
    if not is_valid_index(idx, w_obj):
        raise PrimitiveFailedError()
    return w_val, idx, w_obj

@primitive(AT)
@stack(2)
def func(stack):
    idx, w_obj = common_at(stack)
    return w_obj.getindexedvar(idx)

@primitive(AT_PUT)
@stack(3)
def func(stack):
    w_val, idx, w_obj = common_at_put(stack)
    w_obj.setindexedvar(idx, w_val)
    return w_val

@primitive(SIZE)
@stack(1)
def func(stack):
    [w_obj] = stack
    if not w_obj.w_class.isindexable():
        raise PrimitiveFailedError()
    return w_obj.size()

@primitive(STRING_AT)
@stack(2)
def func(stack):
    idx, w_obj = common_at(stack)
    byte = w_obj.getbyte(idx)
    return fimg.CharacterTable[byte]

@primitive(STRING_AT_PUT)
@stack(3)
def func(stack):
    w_val, idx, w_obj = common_at_put(stack)
    if w_val.w_class is not ct.w_Character:
        raise PrimitiveFailedError()
    w_obj.setbyte(idx, fimg.ord_w_char(w_val))
    return w_val

@primitive(OBJECT_AT)
@stack(2)
def func(stack):
    [w_idx, w_rcvr] = stack
    idx = unwrap_int(w_idx)
    if idx < 0 or idx >= w_rcvr.w_class.instvarsize:
        raise PrimitiveFailedError()
    return w_rcvr.getnamedvar(idx)

@primitive(OBJECT_AT_PUT)
@stack(3)
def func(stack):
    [w_val, w_idx, w_rcvr] = stack
    idx = unwrap_int(w_idx)
    if idx < 0 or idx >= w_rcvr.w_class.instvarsize:
        raise PrimitiveFailedError()
    w_rcvr.setnamedvar(idx, w_val)
    return w_val

# ___________________________________________________________________________
# Boolean Primitives

LESSTHAN = 3
GREATERTHAN = 4
LESSOREQUAL = 5
GREATEROREQUAL = 6
EQUAL = 7
NOTEQUAL = 8

FLOAT_LESSTHAN = 43
FLOAT_GREATERTHAN = 44
FLOAT_LESSOREQUAL = 45
FLOAT_GREATEROREQUAL = 46
FLOAT_EQUAL = 47
FLOAT_NOTEQUAL = 48
    
bool_ops = {
    LESSTHAN: operator.lt,
    GREATERTHAN: operator.gt,
    LESSOREQUAL: operator.le,
    GREATEROREQUAL:operator.ge,
    EQUAL: operator.eq,
    NOTEQUAL: operator.ne
    }
for (code,op) in bool_ops.items():
    @primitive(code)
    @stack(2)
    def func(stack, op=op): # n.b. capture op value
        [w_v2, w_v1] = stack
        v1 = unwrap_int(w_v1)
        v2 = unwrap_int(w_v2)
        res = op(v1, v2)
        w_res = fimg.wrap_bool(res)
        return w_res

for (code,op) in bool_ops.items():
    @primitive(code+_FLOAT_OFFSET)
    @stack(2)
    def func(stack, op=op): # n.b. capture op value
        [w_v2, w_v1] = stack
        v1 = unwrap_float(w_v1)
        v2 = unwrap_float(w_v2)
        res = op(v1, v2)
        w_res = fimg.wrap_bool(res)
        return w_res
