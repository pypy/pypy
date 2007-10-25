import operator
import math
from pypy.lang.smalltalk import model, shadow
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import objtable
from pypy.rlib import rarithmetic

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
        return w_obj.fetch(idx)
    elif isinstance(w_obj, model.W_WordsObject):
        return objtable.wrap_int(w_obj.getword(idx))
    elif isinstance(w_obj, model.W_BytesObject):
        return objtable.wrap_int(w_obj.getbyte(idx))
    raise PrimitiveFailedError()

def assert_bounds(n0, minimum, maximum):
    if not minimum <= n0 < maximum:
        raise PrimitiveFailedError()

def assert_valid_index(n0, w_obj):
    assert_bounds(n0, 0, w_obj.size())

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
        assert code not in prim_table
        prim_table[code] = func
        return func
    return decorator

def stack(n):
    def decorator(wrapped):
        def result(args):
            frame = args.interp.w_active_context
            start = len(frame.stack) - n
            if start < 0:
                raise PrimitiveFailedError()   # not enough arguments
            items = frame.stack[start:]
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

bitwise_binary_ops = {
    BIT_AND: operator.and_,
    BIT_OR: operator.or_,
    BIT_XOR: operator.xor,
    }
for (code,op) in bitwise_binary_ops.items():
    def make_func(op):
        @primitive(code)
        @stack(2)
        def func(args, (w_receiver, w_argument)):
            receiver = unwrap_int(w_receiver)
            argument = unwrap_int(w_argument)
            res = op(receiver, argument)
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
# NB: 43 ... 48 are implemented above
FLOAT_MULTIPLY = 49
FLOAT_DIVIDE = 50
FLOAT_TRUNCATED = 51
# OPTIONAL: 52, 53
FLOAT_TIMES_TWO_POWER = 54
FLOAT_SQUARE_ROOT = 55
FLOAT_SIN = 56
FLOAT_ARCTAN = 57
FLOAT_LOG_N = 58
FLOAT_EXP = 59

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

@primitive(FLOAT_TIMES_TWO_POWER)
@stack(2)
def func(args, (w_rcvr,w_arg,)): 
    rcvr = unwrap_float(w_rcvr)
    arg = unwrap_int(w_arg)
    w_res = objtable.wrap_float(math.ldexp(rcvr,arg))
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

@primitive(FLOAT_EXP)
@stack(1)
def func(args, (w_float,)): 
    f = unwrap_float(w_float)
    w_res = objtable.wrap_float(math.exp(f))
    return w_res


# ___________________________________________________________________________
# Subscript and Stream Primitives

AT = 60
AT_PUT = 61
SIZE = 62
STRING_AT = 63
STRING_AT_PUT = 64

def common_at((w_obj, w_index1)):
    index1 = unwrap_int(w_index1)
    assert_valid_index(index1-1, w_obj)
    return w_obj, index1-1

def common_at_put((w_obj, w_idx, w_val)):
    idx = unwrap_int(w_idx)
    assert_valid_index(idx-1, w_obj)
    return w_obj, idx-1, w_val

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
    return wrap_int(w_obj.size())

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
def func(args, (w_rcvr, w_n1)):
    n0 = unwrap_int(w_n1) - 1
    assert_bounds(n0, 0, w_rcvr.shadow_of_my_class().instance_size)
    return w_rcvr.fetch(n0)

@primitive(OBJECT_AT_PUT)
@stack(3)
def func(args, (w_rcvr, w_n1, w_val)):
    n0 = unwrap_int(w_n1) - 1
    assert_bounds(n0, 0, w_rcvr.shadow_of_my_class().instance_size)
    w_rcvr.store(n0, w_val)
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
    # XXX this doesn't look correct.  Our guess is that INST_VAR_AT
    # is used to access *only* the fixed length fields.
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
    return wrap_int(w_rcvr.gethash())

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
    # XXX this is bogus in the presence of (our implementation of) become,
    # as we might plan to implement become by copying all fields from one
    # object to the other
    return objtable.wrap_bool(w_arg is w_rcvr)

@primitive(CLASS)
@stack(1)
def func(args, (w_obj,)):
    return w_obj.getclass()

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
    w_arg_class = w_arg.getclass()
    w_rcvr_class = w_rcvr.getclass()

    # We should fail if:

    # 1. Rcvr or arg are SmallIntegers
    if (w_arg_class == classtable.w_SmallInteger or
        w_rcvr_class == classtable.w_SmallInteger):
        raise PrimitiveFailedError()

    # 2. Rcvr is an instance of a compact class and argument isn't
    # or vice versa (?)

    # 3. Format of rcvr is different from format of argument
    raise PrimitiveNotYetWrittenError()     # XXX needs to work in the shadows
    if w_arg_class.format != w_rcvr_class.format:
        raise PrimitiveFailedError()

    # Fail when argument class is fixed and rcvr's size differs from the
    # size of an instance of the arg
    if w_arg_class.instsize() != w_rcvr_class.instsize():
        raise PrimitiveFailedError()

    w_rcvr.w_class = w_arg.w_class
    return 

# ___________________________________________________________________________
# Squeak Miscellaneous Primitives (128-149)
FULL_GC = 130
INC_GC = 131

def fake_bytes_left():
    return wrap_int(2**20) # XXX we don't know how to do this :-(

@primitive(INC_GC) # XXX the same for now
@primitive(FULL_GC)
@stack(1) # Squeak pops the arg and ignores it ... go figure
def func(args, (w_arg,)):
    from pypy.rlib import rgc
    rgc.collect()
    return fake_bytes_left()

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
        def make_func(const):
            @primitive(code)
            @stack(1)
            def func(args, stack):
                return const
        make_func(const)
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
    frame = args.interp.w_active_context
    argcnt = unwrap_int(w_argcnt)

    # From B.B.: If receiver is a MethodContext, then it becomes
    # the new BlockContext's home context.  Otherwise, the home
    # context of the receiver is used for the new BlockContext.
    # Note that in our impl, MethodContext.w_home == self
    if not isinstance(w_context, model.W_ContextPart):
        raise PrimitiveFailedError()
    w_method_context = w_context.w_home

    # The block bytecodes are stored inline: so we skip past the
    # byteodes to invoke this primitive to find them (hence +2)
    initialip = frame.pc + 2
    w_new_context = model.W_BlockContext(
        w_method_context, objtable.w_nil, argcnt, initialip)
    return w_new_context
    
@primitive(PRIMITIVE_VALUE)
def func(args):

    # If nargs == 4, stack looks like:
    #  3      2       1      0
    #  Rcvr | Arg 0 | Arg1 | Arg 2
    #
    
    frame = args.interp.w_active_context
    
    # Validate that we have a block on the stack and that it received
    # the proper number of arguments:
    w_block_ctx = frame.peek(args.argument_count-1)
    if not isinstance(w_block_ctx, model.W_BlockContext):
        raise PrimitiveFailedError()
    exp_arg_cnt = w_block_ctx.expected_argument_count()
    if args.argument_count != exp_arg_cnt:
        raise PrimitiveFailedError()

    # Initialize the block stack from the contents of the stack:
    #   Don't bother to copy the 'self' argument
    block_args = frame.pop_n(exp_arg_cnt)
    w_block_ctx.push_all(block_args)

    # Set some fields
    w_block_ctx.pc = w_block_ctx.initialip
    w_block_ctx.w_sender = frame
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
