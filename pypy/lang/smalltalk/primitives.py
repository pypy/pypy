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

def subscript(idx, w_obj):
    if isinstance(w_obj, model.W_PointersObject):
        return w_obj.getindexedvar(idx)
    elif isinstance(w_obj, model.W_WordsObject):
        return fimg.wrap_int(w_obj.getword(idx))
    elif isinstance(w_obj, model.W_BytesObject):
        return fimg.wrap_int(w_obj.getbyte(idx))
    raise PrimitiveFailedError()

def assert_bounds(idx, minb, maxb):
    if idx < minb or idx >= maxb:
        raise PrimitiveFailedError()

def assert_valid_index(idx, w_obj):
    assert_bounds(idx, 0, w_obj.size())

# ___________________________________________________________________________
# Primitive table: it is filled in at initialization time with the
# primitive functions.  Each primitive function takes a single argument,
# the frame (a W_ContextFrame object); the function either completes, and
# returns a result, or throws a PrimitiveFailedError.

prim_table = [None] * 576 # Squeak has primitives all the way up to 575

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
        
        w_res = fimg.wrap_int(res)
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

def common_at(stack):
    [w_idx, w_obj] = stack
    idx = unwrap_int(w_idx)
    assert_valid_index(idx, w_obj)
    return idx, w_obj

def common_at_put(stack):
    [w_val, w_idx, w_obj] = stack
    idx = unwrap_int(w_idx)
    assert_valid_index(idx, w_obj)
    return w_val, idx, w_obj

@primitive(AT)
@stack(2)
def func(stack):
    idx, w_obj = common_at(stack)
    return w_obj.fetch(idx)

@primitive(AT_PUT)
@stack(3)
def func(stack):
    w_val, idx, w_obj = common_at_put(stack)
    w_obj.store(idx, w_val)
    return w_val

@primitive(SIZE)
@stack(1)
def func(stack):
    [w_obj] = stack
    if not w_obj.w_class.isvariable():
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

# ___________________________________________________________________________
# Storage Management Primitives

OBJECT_AT = 68
OBJECT_AT_PUT = 69
NEW = 70
NEW_WITH_ARG = 71
ARRAY_BECOME_ONE_WAY = 72     # Blue Book: primitiveBecome
INST_VAR_AT = 73
INST_VAR_AT_PUT = 74
AS_OOP = 75                  
STORE_STACKP = 76             # Blue Book: primitiveAsObject
SOME_INSTANCE = 77
NEXT_INSTANCE = 78

@primitive(OBJECT_AT)
@stack(2)
def func(stack):
    [w_idx, w_rcvr] = stack
    idx = unwrap_int(w_idx)
    assert_bounds(idx, 0, w_rcvr.w_class.instvarsize)
    return w_rcvr.getnamedvar(idx)

@primitive(OBJECT_AT_PUT)
@stack(3)
def func(stack):
    [w_val, w_idx, w_rcvr] = stack
    idx = unwrap_int(w_idx)
    assert_bounds(idx, 0, w_rcvr.w_class.instvarsize)
    w_rcvr.setnamedvar(idx, w_val)
    return w_val

@primitive(NEW)
@stack(1)
def func(stack):
    [w_cls] = stack
    if not isinstance(w_cls, model.W_Class) or w_cls.isvariable():
        raise PrimitiveFailedError()
    return w_cls.new()

@primitive(NEW_WITH_ARG)
@stack(2)
def func(stack):
    [w_size, w_cls] = stack
    if not isinstance(w_cls, model.W_Class) or not w_cls.isvariable():
        raise PrimitiveFailedError()
    size = unwrap_int(w_size)
    return w_cls.new(size)

@primitive(ARRAY_BECOME_ONE_WAY)
def func(frame):
    raise PrimitiveNotYetWrittenError

@primitive(INST_VAR_AT)
@stack(2)
def func(stack):
    # I *think* this is the correct behavior, but I'm not quite sure.
    # Might be restricted to fixed length fields?
    [w_idx, w_rcvr] = stack
    idx = unwrap_int(w_idx)
    w_cls = w_rcvr.w_class
    if idx < 0:
        raise PrimitiveFailedError()
    if idx < w_cls.instvarsize:
        return w_rcvr.getnamedvar(idx)
    idx -= w_cls.instvarsize
    if idx < w_rcvr.size():
        return subscript(idx, w_rcvr)
    raise PrimitiveFailedError()

@primitive(INST_VAR_AT_PUT)
def func(frame):
    raise PrimitiveNotYetWrittenError()

@primitive(AS_OOP)
@stack(1)
def func(stack):
    [w_rcvr] = stack
    if isinstance(w_rcvr, model.W_SmallInteger):
        raise PrimitiveFailedError()
    return w_rcvr.w_hash

@primitive(STORE_STACKP)
@stack(2)
def func(stack):
    # This primitive seems to resize the stack.  I don't think this is
    # really relevant in our implementation.
    raise PrimitiveNotYetWrittenError()

@primitive(SOME_INSTANCE)
@stack(1)
def func(stack):
    # This primitive returns some instance of the class on the stack.
    # Not sure quite how to do this; maintain a weak list of all
    # existing instances or something?
    [w_class] = stack
    raise PrimitiveNotYetWrittenError()

@primitive(NEXT_INSTANCE)
@stack(1)
def func(stack):
    # This primitive is used to iterate through all instances of a class:
    # it returns the "next" instance after w_obj.
    [w_obj] = stack
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
    
# ___________________________________________________________________________
# Quick Push Const Primitives

PUSH_SELF = 256
PUSH_TRUE = 257
PUSH_FALSE = 258
PUSH_NIL = 259
PUSH_MINUS_ONE = 260
PUSH_ZERO = 261
PUSH_ONE = 262
PUSH_TWO = 263

@primitive(PUSH_SELF)
@stack(1)
def func(stack):
    [w_self] = stack
    return w_self

def define_const_primitives():
    for (code, const) in [
        (PUSH_TRUE, fimg.w_true),
        (PUSH_FALSE, fimg.w_false),
        (PUSH_NIL, fimg.w_nil),
        (PUSH_MINUS_ONE, fimg.w_mone),
        (PUSH_ZERO, fimg.w_zero),
        (PUSH_ONE, fimg.w_one),
        (PUSH_TWO, fimg.w_two),
        ]:
        @primitive(code)
        @stack(1)
        def func(stack, const=const):  # n.b.: capture const
            return const
define_const_primitives()
        
