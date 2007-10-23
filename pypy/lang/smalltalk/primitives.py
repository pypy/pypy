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
    def f(func):
        prim_table[code] = func
        return func
    return f

# ___________________________________________________________________________
# Small Integer Primitives

ADD = 1
SUBTRACT = 2

math_ops = {
    ADD: operator.add,
    SUBTRACT: operator.sub
    }
for (code,op) in math_ops.items():
    def func(frame, op=op): # n.b. capture op value
        w_v1 = frame.peek(1)
        w_v2 = frame.peek(0)
        v1 = unwrap_int(w_v1)
        v2 = unwrap_int(w_v2)
        res = op(v1, v2)
        
        # Emulate the bounds of smalltalk tagged integers:
        if res > 1073741823: raise PrimitiveFailedError()
        if res < -1073741824: raise PrimitiveFailedError()
        
        w_res = fimg.small_int(res)
        frame.pop_n(2)
        return w_res
    prim_table[code] = func

MAKE_POINT = 18
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
    def func(frame, op=op): # n.b. capture op value
        w_v1 = frame.peek(0)
        w_v2 = frame.peek(1)
        v1 = unwrap_float(w_v1)
        v2 = unwrap_float(w_v2)
        w_res = fimg.wrap_float(op(v1, v2))
        frame.pop_n(2)
        return w_res
    prim_table[code] = func

# ___________________________________________________________________________
# Subscript and Stream Primitives

AT = 60
AT_PUT = 61
SIZE = 62
STRING_AT = 63
STRING_AT_PUT = 64

def common_at(frame):
    w_idx = frame.peek(0)
    w_obj = frame.peek(1)
    idx = unwrap_int(w_idx)
    if not is_valid_index(idx, w_obj):
        raise PrimitiveFailedError()
    frame.pop_n(2)
    return idx, w_obj

def common_at_put(frame):
    w_val = frame.peek(0)
    w_idx = frame.peek(1)
    w_obj = frame.peek(2)
    idx = unwrap_int(w_idx)
    if not is_valid_index(idx, w_obj):
        raise PrimitiveFailedError()
    frame.pop_n(2)
    return idx, w_obj

@primitive(AT)
def func(frame):
    idx, w_obj = common_at(frame)
    return w_obj.getindexedvar(idx)

@primitive(AT_PUT)
def func(frame):
    w_val = frame.peek(0)
    w_idx = frame.peek(1)
    w_obj = frame.peek(2)
    idx = unwrap_int(w_idx)
    if not is_valid_index(idx, w_obj):
        raise PrimitiveFailedError()
    w_obj.setindexedvar(idx, w_val)
    frame.pop_n(3)
    return w_val

@primitive(SIZE)
def func(frame):
    w_obj = frame.peek(0)
    if not w_obj.w_class.isindexable():
        raise PrimitiveFailedError()
    frame.pop_n(1)
    return w_obj.size()

@primitive(STRING_AT)
def func(frame):
    idx, w_obj = common_at(frame)
    byte = w_obj.getbyte(idx)
    return fimg.CharacterTable[byte]

@primitive(STRING_AT_PUT)
def func(frame):
    raise PrimitiveNotYetWrittenError()

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
    def func(frame, op=op): # n.b. capture op value
        w_v1 = frame.peek(1)
        w_v2 = frame.peek(0)
        v1 = unwrap_int(w_v1)
        v2 = unwrap_int(w_v2)
        res = op(v1, v2)
        
        w_res = fimg.wrap_bool(res)
        frame.pop_n(2)
        return w_res
    prim_table[code] = func

for (code,op) in bool_ops.items():
    def func(frame, op=op): # n.b. capture op value
        w_v1 = frame.peek(1)
        w_v2 = frame.peek(0)
        v1 = unwrap_float(w_v1)
        v2 = unwrap_float(w_v2)
        res = op(v1, v2)
        
        w_res = fimg.wrap_bool(res)
        frame.pop_n(2)
        return w_res
    prim_table[code+_FLOAT_OFFSET] = func
