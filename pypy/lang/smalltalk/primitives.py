import operator
import math
from pypy.lang.smalltalk import model, shadow
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import objtable
from pypy.rlib import rarithmetic

from pypy.lang.smalltalk.constants import \
     BLKCTX_CALLER_INDEX, \
     BLKCTX_INSTRUCTION_POINTER_INDEX, \
     BLKCTX_STACK_POINTER_INDEX, \
     BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX, \
     BLKCTX_INITIAL_IP_INDEX, \
     BLKCTX_HOME_INDEX, \
     BLKCTX_TEMP_FRAME_START

class PrimitiveFailedError(Exception):
    pass

class PrimitiveNotYetWrittenError(PrimitiveFailedError):
    pass

def unwrap_float(w_v):
    if isinstance(w_v, model.W_Float): return w_v.value
    elif isinstance(w_v, model.W_SmallInteger): return float(w_v.value)
    raise PrimitiveFailedError()

def subscript(idx, w_obj):
    if isinstance(w_obj, model.W_PointersObject):
        return w_obj.getindexedvar(idx)
    elif isinstance(w_obj, model.W_WordsObject):
        return objtable.wrap_int(w_obj.getword(idx))
    elif isinstance(w_obj, model.W_BytesObject):
        return objtable.wrap_int(w_obj.getbyte(idx))
    raise PrimitiveFailedError()

def assert_bounds(idx, minb, maxb):
    if idx < minb or idx >= maxb:
        raise PrimitiveFailedError()

def assert_valid_index(idx, w_obj):
    assert_bounds(idx, 0, w_obj.size())

# ___________________________________________________________________________
# Primitive table: it is filled in at initialization time with the
# primitive functions.  Each primitive function takes a single
# argument, an instance of the Args class below; the function either
# completes, and returns a result, or throws a PrimitiveFailedError.

def raise_failing_default(args):
	raise PrimitiveFailedError

# Squeak has primitives all the way up to 575
# So all optional primitives will default to the bytecode implementation
prim_table = [raise_failing_default] * 576

class Args:
    def __init__(self, interp, argument_count):
        self.interp = interp
        self.argument_count = argument_count

def primitive(code):
    def decorator(func):
        prim_table[code] = func
        return func
    return decorator

def stack(n):
    def decorator(wrapped):
        def result(args):
            frame = args.interp.w_active_context
            items = frame.stack[len(frame.stack)-n:]
            res = wrapped(args, items)
            frame.pop_n(n)   # only if no exception occurs!
            return res
        return result
    return decorator

# ___________________________________________________________________________
# SmallInteger Primitives

def unwrap_int(w_value):
    if isinstance(w_value, model.W_SmallInteger): 
        return w_value.value
    raise PrimitiveFailedError()

def wrap_int(value):
    if value > 1073741823:
        raise PrimitiveFailedError()
    if value < -1073741824:
        raise PrimitiveFailedError()
    return objtable.wrap_int(value)
    
ADD         = 1
SUBTRACT    = 2
MULTIPLY    = 9
DIVIDE      = 10
MOD         = 11
DIV         = 12
QUO         = 13
BIT_AND     = 14
BIT_OR      = 15
BIT_XOR     = 16
BIT_SHIFT   = 17

math_ops = {
    ADD: operator.add,
    SUBTRACT: operator.sub,
    MULTIPLY: operator.mul,
    BIT_AND: operator.and_,
    BIT_OR: operator.or_,
    BIT_XOR: operator.xor
    }
for (code,op) in math_ops.items():
    def make_func(op):
        @primitive(code)
        @stack(2)
        def func(args, (w_receiver, w_argument)):
            receiver = unwrap_int(w_receiver)
            argument = unwrap_int(w_argument)
            try:
                res = rarithmetic.ovfcheck(op(receiver, argument))
            except OverflowError:
                raise PrimitiveFailedError()
            return wrap_int(res)
    make_func(op)

# #/ -- return the result of a division, only succeed if the division is exact
@primitive(DIVIDE)
@stack(2)
def func(args, (w_receiver, w_argument)):
    receiver = unwrap_int(w_receiver)
    argument = unwrap_int(w_argument)
    if argument == 0:
        raise PrimitiveFailedError()
    if receiver % argument != 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver // argument)

# #\\ -- return the remainder of a division
@primitive(MOD)
@stack(2)
def func(args, (w_receiver, w_argument)):
    receiver = unwrap_int(w_receiver)
    argument = unwrap_int(w_argument)
    if argument == 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver % argument)

# #// -- return the result of a division, rounded towards negative zero
@primitive(DIV)
@stack(2)
def func(args, (w_receiver, w_argument)):
    receiver = unwrap_int(w_receiver)
    argument = unwrap_int(w_argument)
    if argument == 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver // argument)
    
# #// -- return the result of a division, rounded towards negative infinity
@primitive(QUO)
@stack(2)
def func(args, (w_receiver, w_argument)):
    receiver = unwrap_int(w_receiver)
    argument = unwrap_int(w_argument)
    if argument == 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver // argument)
    
# #bitShift: -- return the shifted value
@primitive(BIT_SHIFT)
@stack(2)
def func(args, (w_receiver, w_argument)):
    receiver = unwrap_int(w_receiver)
    argument = unwrap_int(w_argument)
    
    # heh, no shifting at all
    if argument == 0:
        return w_receiver

    # left shift, must fail if we loose bits beyond 32
    if argument > 0:
        shifted = receiver << argument
        if (shifted >> argument) != receiver:
            raise PrimitiveFailedError()
        return wrap_int(shifted)
            
    # right shift, ok to lose bits
    else:
        return wrap_int(receiver >> -argument)
   

# ___________________________________________________________________________
# Float Primitives

_FLOAT_OFFSET = 40
FLOAT_ADD = 41
FLOAT_SUBTRACT = 42
FLOAT_MULTIPLY = 49
FLOAT_DIVIDE = 50
FLOAT_TRUNCATED = 51
FLOAT_SQUARE_ROOT = 55
FLOAT_SIN = 56
FLOAT_ARCTAN = 57
FLOAT_LOG_N = 58

math_ops = {
    FLOAT_ADD: operator.add,
    FLOAT_SUBTRACT: operator.sub,
    FLOAT_MULTIPLY: operator.mul,
    FLOAT_DIVIDE: operator.div,
    }
for (code,op) in math_ops.items():
    def make_func(op):
        @primitive(code)
        @stack(2)
        def func(args, (w_v1, w_v2)):
            v1 = unwrap_float(w_v1)
            v2 = unwrap_float(w_v2)
            w_res = objtable.wrap_float(op(v1, v2))
            return w_res
    make_func(op)

@primitive(FLOAT_TRUNCATED)
@stack(1)
def func(args, (w_float,)): 
    f = unwrap_float(w_float)
    w_res = objtable.wrap_int(int(f))
    return w_res

@primitive(FLOAT_SQUARE_ROOT)
@stack(1)
def func(args, (w_float,)): 
    f = unwrap_float(w_float)
    if f < 0.0:
        raise PrimitiveFailedError
    w_res = objtable.wrap_float(math.sqrt(f))
    return w_res

@primitive(FLOAT_SIN)
@stack(1)
def func(args, (w_float,)): 
    f = unwrap_float(w_float)
    w_res = objtable.wrap_float(math.sin(f))
    return w_res

@primitive(FLOAT_ARCTAN)
@stack(1)
def func(args, (w_float,)): 
    f = unwrap_float(w_float)
    w_res = objtable.wrap_float(math.atan(f))
    return w_res

@primitive(FLOAT_LOG_N)
@stack(1)
def func(args, (w_float,)): 
    f = unwrap_float(w_float)
    if f == 0:
        res = -rarithmetic.INFINITY
    elif f < 0:
        res = rarithmetic.NAN
    else:
        res = math.log(f)
    return objtable.wrap_float(res)

# ___________________________________________________________________________
# Subscript and Stream Primitives

AT = 60
AT_PUT = 61
SIZE = 62
STRING_AT = 63
STRING_AT_PUT = 64

def common_at((w_obj, w_idx)):
    idx = unwrap_int(w_idx)
    # XXX should be idx-1, probably
    assert_valid_index(idx, w_obj)
    return w_obj, idx

def common_at_put((w_obj, w_idx, w_val)):
    idx = unwrap_int(w_idx)
    # XXX should be idx-1, probably
    assert_valid_index(idx, w_obj)
    return w_obj, idx, w_val

@primitive(AT)
@stack(2)
def func(args, stack):
    [w_obj, idx] = common_at(stack)
    return w_obj.fetch(idx)

@primitive(AT_PUT)
@stack(3)
def func(args, stack):
    [w_obj, idx, w_val] = common_at_put(stack)
    w_obj.store(idx, w_val)
    return w_val

@primitive(SIZE)
@stack(1)
def func(args, (w_obj,)):
    if not w_obj.shadow_of_my_class().isvariable():
        raise PrimitiveFailedError()
    return w_obj.size()

@primitive(STRING_AT)
@stack(2)
def func(args, stack):
    w_obj, idx = common_at(stack)
    byte = w_obj.getbyte(idx)
    return objtable.CharacterTable[byte]

@primitive(STRING_AT_PUT)
@stack(3)
def func(args, stack):
    w_obj, idx, w_val = common_at_put(stack)
    if w_val.getclass() is not classtable.w_Character:
        raise PrimitiveFailedError()
    w_obj.setbyte(idx, objtable.ord_w_char(w_val))
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
NEW_METHOD = 79

@primitive(OBJECT_AT)
@stack(2)
def func(args, (w_rcvr, w_idx)):
    idx = unwrap_int(w_idx)
    # XXX should be idx-1, probably
    assert_bounds(idx, 0, w_rcvr.shadow_of_my_class().instance_size)
    return w_rcvr.fetch(idx)

@primitive(OBJECT_AT_PUT)
@stack(3)
def func(args, (w_rcvr, w_idx, w_val)):
    idx = unwrap_int(w_idx)
    # XXX should be idx-1, probably
    assert_bounds(idx, 0, w_rcvr.shadow_of_my_class().instance_size)
    w_rcvr.store(idx, w_val)
    return w_val

@primitive(NEW)
@stack(1)
def func(args, (w_cls,)):
    shadow = w_cls.as_class_get_shadow()
    if shadow.isvariable():
        raise PrimitiveFailedError()
    return shadow.new()

@primitive(NEW_WITH_ARG)
@stack(2)
def func(args, (w_cls, w_size)):
    shadow = w_cls.as_class_get_shadow()
    if not shadow.isvariable():
        raise PrimitiveFailedError()
    size = unwrap_int(w_size)
    return shadow.new(size)

@primitive(ARRAY_BECOME_ONE_WAY)
def func(args):
    raise PrimitiveNotYetWrittenError

@primitive(INST_VAR_AT)
@stack(2)
def func(args, (w_rcvr, w_idx)):
    # I *think* this is the correct behavior, but I'm not quite sure.
    # Might be restricted to fixed length fields?
    idx = unwrap_int(w_idx)
    shadow = w_rcvr.shadow_of_my_class()
    if idx < 0:
        raise PrimitiveFailedError()
    if idx < shadow.instsize():
        return w_rcvr.fetch(idx)
    idx -= shadow.instsize()
    if idx < w_rcvr.size():
        return subscript(idx, w_rcvr)
    raise PrimitiveFailedError()

@primitive(INST_VAR_AT_PUT)
def func(args):
    raise PrimitiveNotYetWrittenError()

@primitive(AS_OOP)
@stack(1)
def func(args, (w_rcvr,)):
    if isinstance(w_rcvr, model.W_SmallInteger):
        raise PrimitiveFailedError()
    return w_rcvr.w_hash

@primitive(STORE_STACKP)
@stack(2)
def func(args, stack):
    # This primitive seems to resize the stack.  I don't think this is
    # really relevant in our implementation.
    raise PrimitiveNotYetWrittenError()

@primitive(SOME_INSTANCE)
@stack(1)
def func(args, (w_class,)):
    # This primitive returns some instance of the class on the stack.
    # Not sure quite how to do this; maintain a weak list of all
    # existing instances or something?
    raise PrimitiveNotYetWrittenError()

@primitive(NEXT_INSTANCE)
@stack(1)
def func(args, (w_obj,)):
    # This primitive is used to iterate through all instances of a class:
    # it returns the "next" instance after w_obj.
    raise PrimitiveNotYetWrittenError()

@primitive(NEW_METHOD)
def func(args):
    raise PrimitiveNotYetWrittenError()

# ___________________________________________________________________________
# Control Primitives

EQUIVALENT = 110
CLASS = 111
BYTES_LEFT = 112
QUIT = 113
EXIT_TO_DEBUGGER = 114
CHANGE_CLASS = 115      # Blue Book: primitiveOopsLeft

@primitive(EQUIVALENT)
@stack(2)
def func(args, (w_arg, w_rcvr)):
    return w_arg == w_rcvr

@primitive(EQUIVALENT)
@stack(1)
def func(args, (w_obj,)):
    return w_obj.w_class

@primitive(BYTES_LEFT)
def func(args):
    raise PrimitiveNotYetWrittenError()

@primitive(QUIT)
def func(args):
    raise PrimitiveNotYetWrittenError()

@primitive(EXIT_TO_DEBUGGER)
def func(args):
    raise PrimitiveNotYetWrittenError()

@primitive(CHANGE_CLASS)
@stack(2)
def func(args, (w_arg, w_rcvr)):
    w_arg_class = w_arg.w_class
    w_rcvr_class = w_rcvr.w_class

    # We should fail if:

    # 1. Rcvr or arg are SmallIntegers
    if (w_arg_class == classtable.w_SmallInteger or
        w_rcvr_class == classtable.w_SmallInteger):
        raise PrimitiveFailedError()

    # 2. Rcvr is an instance of a compact class and argument isn't
    # or vice versa (?)

    # 3. Format of rcvr is different from format of argument
    if w_arg_class.format != w_rcvr_class.format:
        raise PrimitiveFailedError()

    # Fail when argument class is fixed and rcvr's size differs from the
    # size of an instance of the arg
    if w_arg_class.instsize() != w_rcvr_class.instsize():
        raise PrimitiveFailedError()

    w_rcvr.w_class = w_arg.w_class
    return 

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
    def make_func(op):
        @primitive(code)
        @stack(2)
        def func(args, (w_v1, w_v2)):
            v1 = unwrap_int(w_v1)
            v2 = unwrap_int(w_v2)
            res = op(v1, v2)
            w_res = objtable.wrap_bool(res)
            return w_res
    make_func(op)

for (code,op) in bool_ops.items():
    def make_func(op):
        @primitive(code+_FLOAT_OFFSET)
        @stack(2)
        def func(args, (w_v1, w_v2)):
            v1 = unwrap_float(w_v1)
            v2 = unwrap_float(w_v2)
            res = op(v1, v2)
            w_res = objtable.wrap_bool(res)
            return w_res
    make_func(op)
    
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
def func(args, stack):
    [w_self] = stack
    return w_self

def define_const_primitives():
    for (code, const) in [
        (PUSH_TRUE, objtable.w_true),
        (PUSH_FALSE, objtable.w_false),
        (PUSH_NIL, objtable.w_nil),
        (PUSH_MINUS_ONE, objtable.w_mone),
        (PUSH_ZERO, objtable.w_zero),
        (PUSH_ONE, objtable.w_one),
        (PUSH_TWO, objtable.w_two),
        ]:
        @primitive(code)
        @stack(1)
        def func(args, stack, const=const):  # n.b.: capture const
            return const
define_const_primitives()
        
# ___________________________________________________________________________
# Control Primitives

PRIMITIVE_BLOCK_COPY = 80
PRIMITIVE_VALUE = 81
PRIMITIVE_VALUE_WITH_ARGS = 82
PRIMITIVE_PERFORM = 83
PRIMITIVE_PERFORM_WITH_ARGS = 84
PRIMITIVE_SIGNAL = 85
PRIMITIVE_WAIT = 86
PRIMITIVE_RESUME = 87
PRIMITIVE_SUSPEND = 88
PRIMITIVE_FLUSH_CACHE = 89

@primitive(PRIMITIVE_BLOCK_COPY)
@stack(2)
def func(args, (w_context, w_argcnt)):
    raise PrimitiveNotYetWrittenError()
    frame = args.interp.w_active_context

    # From B.B.: If receiver is a MethodContext, then it becomes
    # the new BlockContext's home context.  Otherwise, the home
    # context of the receiver is used for the new BlockContext.
    if w_context.getclass() == classtable.w_BlockContext:
        w_method_context = w_context.fetch(BLKCTX_HOME_INDEX)
    else:
        w_method_context = w_context

    # The block bytecodes are stored inline: so we skip past the
    # byteodes to invoke this primitive to find them (hence +3)
    w_new_context = classtable.w_BlockContext.as_class_get_shadow().new(
        unwrap_int(w_argcnt))
    initialip = frame.pc + 3

    # Initialize various fields.
    w_new_context.store(BLKCTX_INITIAL_IP_INDEX, initialip)
    w_new_context.store(BLKCTX_INSTRUCTION_POINTER_INDEX, initialip)
    w_new_context.store(BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX, w_argcnt)
    w_new_context.store(BLKCTX_HOME_INDEX, w_method_context)
    return w_new_context
    
@primitive(PRIMITIVE_VALUE)
def func(args):
    raise PrimitiveNotYetWrittenError()

    # If nargs == 4, stack looks like:
    #  3      2       1      0
    #  Rcvr | Arg 0 | Arg1 | Arg 2
    #
    
    w_block_ctx = args.interp.w_active_context.peek(args.argument_count-1)

    w_exp_arg_cnt = w_block_ctx.fetch(BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX)
    exp_arg_cnt = unwrap_int(w_exp_arg_cnt)
    if args.argument_count != exp_arg_cnt:
        raise PrimitiveFailedError()

    # Copy the values from the stack such that the most recently pushed
    # item (index 0) ends up in slot BLKCTX_TEMP_FRAME_START + nargs - 1
    for idx in range(exp_arg_cnt - 1):
        w_block_ctx.store(
            BLKCTX_TEMP_FRAME_START+idx,     
            w_block_ctx.fetch(exp_arg_cnt - idx - 1))

    # Set some fields
    w_initial_ip = w_block_ctx.fetch(BLKCTX_INITIAL_IP_INDEX)
    w_block_ctx.store(BLKCTX_INSTRUCTION_POINTER_INDEX, w_initial_ip)
    w_block_ctx.store(BLKCTX_STACK_POINTER_INDEX, w_exp_arg_cnt)
    w_block_ctx.store(BLKCTX_CALLER_INDEX, args.interp.w_active_context)
    args.interp.w_active_context = w_block_ctx
    
@primitive(PRIMITIVE_VALUE_WITH_ARGS)
@stack(2)
def func(args, (w_rcvr, w_args)):
    raise PrimitiveNotYetWrittenError()

@primitive(PRIMITIVE_PERFORM)
@stack(2)
def func(args, (w_rcvr, w_sel)):
    # XXX we can implement this when lookup on shadow class is done
    raise PrimitiveNotYetWrittenError()

@primitive(PRIMITIVE_PERFORM_WITH_ARGS)
@stack(3)
def func(args, (w_rcvr, w_sel, w_args)):
    raise PrimitiveNotYetWrittenError()

@primitive(PRIMITIVE_SIGNAL)
@stack(1)
def func(args, (w_rcvr,)):
    raise PrimitiveNotYetWrittenError()
    
@primitive(PRIMITIVE_WAIT)
@stack(1)
def func(args, (w_rcvr,)):
    raise PrimitiveNotYetWrittenError()
    
@primitive(PRIMITIVE_RESUME)
@stack(1)
def func(args, (w_rcvr,)):
    raise PrimitiveNotYetWrittenError()

@primitive(PRIMITIVE_SUSPEND)
@stack(1)
def func(args, (w_rcvr,)):
    raise PrimitiveNotYetWrittenError()

@primitive(PRIMITIVE_FLUSH_CACHE)
@stack(1)
def func(args, (w_rcvr,)):
    raise PrimitiveNotYetWrittenError()
