import inspect
import math
import operator
from pypy.lang.smalltalk import model, shadow
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk import constants
from pypy.rlib import rarithmetic

class PrimitiveFailedError(Exception):
    pass

class PrimitiveNotYetWrittenError(PrimitiveFailedError):
    pass

def unwrap_float(w_v):
    if isinstance(w_v, model.W_Float): return w_v.value
    elif isinstance(w_v, model.W_SmallInteger): return float(w_v.value)
    raise PrimitiveFailedError()

def w_subscript(w_obj, idx):
    """
    Rather cryptically named function which retrieves an indexed field
    from the object, wrapping as necessary depending on the format of
    the object so that the result can be returned.
    """
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
# primitive functions.  Each primitive function takes two
# arguments, an interp and an argument_count
# completes, and returns a result, or throws a PrimitiveFailedError.
def make_failing(code):
    def raise_failing_default(interp, argument_count):
#        print "Primitive failed", code
        raise PrimitiveFailedError
    return raise_failing_default

# Squeak has primitives all the way up to 575
# So all optional primitives will default to the bytecode implementation
prim_table = [make_failing(i) for i in range(576)]

# indicates that what is pushed is an index1, but it is unwrapped and
# converted to an index0 
index1_0 = object()

def expose_primitive(code, unwrap_spec=None):
    # some serious magic, don't look
    from pypy.rlib.unroll import unrolling_iterable
    # heuristics to give it a nice name
    name = None
    for key, value in globals().iteritems():
        if isinstance(value, int) and value == code and key == key.upper():
            if name is not None:
                # refusing to guess
                name = "unknown"
            else:
                name = key

    # Because methods always have a receiver, an unwrap_spec of [] is a bug
    assert unwrap_spec is None or unwrap_spec

    def decorator(func):
        assert code not in prim_table
        func.func_name = "prim_" + name
        if unwrap_spec is None:
            prim_table[code] = func
            return func
        for spec in unwrap_spec:
            assert spec in (int, float, object, index1_0, str)
        len_unwrap_spec = len(unwrap_spec)
        assert (len_unwrap_spec == len(inspect.getargspec(func)[0]) + 1,
                "wrong number of arguments")
        unrolling_unwrap_spec = unrolling_iterable(enumerate(unwrap_spec))
        def wrapped(interp, argument_count_m1):
            argument_count = argument_count_m1 + 1 # to account for the rcvr
            frame = interp.w_active_context
            assert argument_count == len_unwrap_spec
            if len(frame.stack) < len_unwrap_spec:
                raise PrimitiveFailedError()
            args = ()
            for i, spec in unrolling_unwrap_spec:
                index = -len_unwrap_spec + i
                arg = frame.stack[index]
                if spec is int:
                    args += (unwrap_int(arg), )
                elif spec is index1_0:
                    args += (unwrap_int(arg)-1, )
                elif spec is float:
                    args += (unwrap_float(arg), )
                elif spec is object:
                    args += (arg, )
                elif spec is str:
                    args += (arg.as_string(), )
                else:
                    assert 0, "this should never happen"
            res = func(interp, *args)
            frame.pop_n(len_unwrap_spec)   # only if no exception occurs!
            return res

        wrapped.func_name = "wrap_prim_" + name
        prim_table[code] = wrapped
        return func
    return decorator

# ___________________________________________________________________________
# SmallInteger Primitives

def unwrap_int(w_value):
    if isinstance(w_value, model.W_SmallInteger): 
        return w_value.value
    raise PrimitiveFailedError()

def wrap_int(value):
    if value > constants.TAGGED_MAXINT:
        raise PrimitiveFailedError()
    if value < constants.TAGGED_MININT:
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
        @expose_primitive(code, unwrap_spec=[int, int])
        def func(interp, receiver, argument):
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
        @expose_primitive(code, unwrap_spec=[int, int])
        def func(interp, receiver, argument):
            res = op(receiver, argument)
            return wrap_int(res)
    make_func(op)

# #/ -- return the result of a division, only succeed if the division is exact
@expose_primitive(DIVIDE, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    if receiver % argument != 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver // argument)

# #\\ -- return the remainder of a division
@expose_primitive(MOD, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver % argument)

# #// -- return the result of a division, rounded towards negative zero
@expose_primitive(DIV, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver // argument)
    
# #// -- return the result of a division, rounded towards negative infinity
@expose_primitive(QUO, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    return wrap_int(receiver // argument)
    
# #bitShift: -- return the shifted value
@expose_primitive(BIT_SHIFT, unwrap_spec=[int, int])
def func(interp, receiver, argument):

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
        @expose_primitive(code, unwrap_spec=[float, float])
        def func(interp, v1, v2):
            w_res = objtable.wrap_float(op(v1, v2))
            return w_res
    make_func(op)

@expose_primitive(FLOAT_TRUNCATED, unwrap_spec=[float])
def func(interp, f): 
    w_res = objtable.wrap_int(int(f))
    return w_res

@expose_primitive(FLOAT_TIMES_TWO_POWER, unwrap_spec=[float, int])
def func(interp, rcvr, arg): 
    w_res = objtable.wrap_float(math.ldexp(rcvr, arg))
    return w_res

@expose_primitive(FLOAT_SQUARE_ROOT, unwrap_spec=[float])
def func(interp, f): 
    if f < 0.0:
        raise PrimitiveFailedError
    w_res = objtable.wrap_float(math.sqrt(f))
    return w_res

@expose_primitive(FLOAT_SIN, unwrap_spec=[float])
def func(interp, f): 
    w_res = objtable.wrap_float(math.sin(f))
    return w_res

@expose_primitive(FLOAT_ARCTAN, unwrap_spec=[float])
def func(interp, f): 
    w_res = objtable.wrap_float(math.atan(f))
    return w_res

@expose_primitive(FLOAT_LOG_N, unwrap_spec=[float])
def func(interp, f): 
    if f == 0:
        res = -rarithmetic.INFINITY
    elif f < 0:
        res = rarithmetic.NAN
    else:
        res = math.log(f)
    return objtable.wrap_float(res)

@expose_primitive(FLOAT_EXP, unwrap_spec=[float])
def func(interp, f): 
    w_res = objtable.wrap_float(math.exp(f))
    return w_res


# ___________________________________________________________________________
# Subscript and Stream Primitives

AT = 60
AT_PUT = 61
SIZE = 62
STRING_AT = 63
STRING_AT_PUT = 64

@expose_primitive(AT, unwrap_spec=[object, index1_0])
def func(interp, w_obj, n0):
    assert_valid_index(n0, w_obj)
    return w_obj.at0(n0)

@expose_primitive(AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_obj, n0, w_val):
    assert_valid_index(n0, w_obj)
    try:
        w_obj.atput0(n0, w_val)
        return w_val
    except model.UnwrappingError:
        raise PrimitiveFailedError()

@expose_primitive(SIZE, unwrap_spec=[object])
def func(interp, w_obj):
    if not w_obj.shadow_of_my_class().isvariable():
        raise PrimitiveFailedError()
    return objtable.wrap_int(w_obj.varsize())

@expose_primitive(STRING_AT, unwrap_spec=[object, index1_0])
def func(interp, w_obj, n0):
    assert_valid_index(n0, w_obj)
    byte = w_obj.getbyte(n0)
    return objtable.CharacterTable[byte]

@expose_primitive(STRING_AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_obj, n0, w_val):
    assert_valid_index(n0, w_obj)
    if w_val.getclass() is not classtable.w_Character:
        raise PrimitiveFailedError()
    w_obj.setbyte(n0, objtable.ord_w_char(w_val))
    return w_val

# ___________________________________________________________________________
# Stream Primitives

NEXT = 65
NEXT_PUT = 66
AT_END = 67

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

@expose_primitive(OBJECT_AT, unwrap_spec=[object, index1_0])
def func(interp, w_rcvr, n0):
    if not isinstance(w_rcvr, model.W_CompiledMethod):
        raise PrimitiveFailedError()
    assert_bounds(n0, 0, len(w_rcvr.literals))
    return w_rcvr.literals[n0]

@expose_primitive(OBJECT_AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_rcvr, n0, w_val):
    if not isinstance(w_rcvr, model.W_CompiledMethod):
        raise PrimitiveFailedError()
    assert_bounds(n0, 0, len(w_rcvr.literals))
    w_rcvr.literals[n0] = w_val
    return w_val

@expose_primitive(NEW, unwrap_spec=[object])
def func(interp, w_cls):
    shadow = w_cls.as_class_get_shadow()
    if shadow.isvariable():
        raise PrimitiveFailedError()
    return shadow.new()

@expose_primitive(NEW_WITH_ARG, unwrap_spec=[object, object])
def func(interp, w_cls, w_size):
    shadow = w_cls.as_class_get_shadow()
    if not shadow.isvariable():
        raise PrimitiveFailedError()
    size = unwrap_int(w_size)
    return shadow.new(size)

@expose_primitive(ARRAY_BECOME_ONE_WAY, unwrap_spec=[object, object])
def func(interp, w_obj1, w_obj2):
    raise PrimitiveNotYetWrittenError

@expose_primitive(INST_VAR_AT, unwrap_spec=[object, index1_0])
def func(interp, w_rcvr, n0):
    "Fetches a fixed field from the object, and fails otherwise"
    shadow = w_rcvr.shadow_of_my_class()
    assert_bounds(n0, 0, shadow.instsize())
    # only pointers have non-0 size
    assert isinstance(w_rcvr, model.W_PointersObject)
    return w_rcvr.fetch(n0)

@expose_primitive(INST_VAR_AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_rcvr, n0, w_value):
    "Stores a value into a fixed field from the object, and fails otherwise"
    shadow = w_rcvr.shadow_of_my_class()
    assert_bounds(n0, 0, shadow.instsize())
    # only pointers have non-0 size    
    assert isinstance(w_rcvr, model.W_PointersObject)
    w_rcvr.store(n0, w_value)
    return w_value

@expose_primitive(AS_OOP, unwrap_spec=[object])
def func(interp, w_rcvr):
    if isinstance(w_rcvr, model.W_SmallInteger):
        raise PrimitiveFailedError()
    return wrap_int(w_rcvr.gethash())

@expose_primitive(STORE_STACKP, unwrap_spec=[object, object])
def func(interp, w_obj1, w_obj2):
    # This primitive seems to resize the stack.  I don't think this is
    # really relevant in our implementation.
    raise PrimitiveNotYetWrittenError()

@expose_primitive(SOME_INSTANCE, unwrap_spec=[object])
def func(interp, w_class):
    # This primitive returns some instance of the class on the stack.
    # Not sure quite how to do this; maintain a weak list of all
    # existing instances or something?
    raise PrimitiveNotYetWrittenError()

@expose_primitive(NEXT_INSTANCE, unwrap_spec=[object])
def func(interp, w_obj):
    # This primitive is used to iterate through all instances of a class:
    # it returns the "next" instance after w_obj.
    raise PrimitiveNotYetWrittenError()

@expose_primitive(NEW_METHOD, unwrap_spec=[object, int, object])
def func(interp, w_class, bytecount, w_header):
    header = unwrap_int(w_header)
    literalcount = ((header >> 10) & 255) + 1
    w_method = w_class.as_class_get_shadow().new(literalcount)
    w_method.literals[constants.METHOD_HEADER_INDEX] = w_header
    for i in range(0,literalcount):
        w_method.literals[i+1] = objtable.w_nil
    w_method.bytes = [None] * bytecount
    return w_method

# ___________________________________________________________________________
# Control Primitives

EQUIVALENT = 110
CLASS = 111
BYTES_LEFT = 112
QUIT = 113
EXIT_TO_DEBUGGER = 114
CHANGE_CLASS = 115      # Blue Book: primitiveOopsLeft

@expose_primitive(EQUIVALENT, unwrap_spec=[object, object])
def func(interp, w_arg, w_rcvr):
    return objtable.wrap_bool(w_arg.equals(w_rcvr))

@expose_primitive(CLASS, unwrap_spec=[object])
def func(interp, w_obj):
    return w_obj.getclass()

@expose_primitive(BYTES_LEFT, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(QUIT, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(EXIT_TO_DEBUGGER, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(CHANGE_CLASS, unwrap_spec=[object, object])
def func(interp, w_arg, w_rcvr):
    w_arg_class = w_arg.getclass()
    w_rcvr_class = w_rcvr.getclass()

    # We should fail if:

    # 1. Rcvr or arg are SmallIntegers
    # XXX this is wrong too
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

@expose_primitive(INC_GC, unwrap_spec=[object])
@expose_primitive(FULL_GC, unwrap_spec=[object])
def func(interp, w_arg): # Squeak pops the arg and ignores it ... go figure
    from pypy.rlib import rgc
    rgc.collect()
    return fake_bytes_left()

#____________________________________________________________________________
# Time Primitives
MILLISECOND_CLOCK = 135
SECONDS_CLOCK = 137

@expose_primitive(MILLISECOND_CLOCK, unwrap_spec=[object])
def func(interp, w_arg):
    import time
    import math
    return wrap_int(int(math.fmod(time.time()*1000, constants.TAGGED_MAXINT/2)))

@expose_primitive(SECONDS_CLOCK, unwrap_spec=[object])
def func(interp, w_arg):
    import time
    return wrap_int(0x23910d6c)      # HACK: too big for a small int!
    #return wrap_int(int(time.time()))

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
        @expose_primitive(code, unwrap_spec=[int, int])
        def func(interp, v1, v2):
            res = op(v1, v2)
            w_res = objtable.wrap_bool(res)
            return w_res
    make_func(op)

for (code,op) in bool_ops.items():
    def make_func(op):
        @expose_primitive(code+_FLOAT_OFFSET, unwrap_spec=[float, float])
        def func(interp, v1, v2):
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

@expose_primitive(PUSH_SELF, unwrap_spec=[object])
def func(interp, w_self):
    # no-op really
    return w_self

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
        @expose_primitive(code, unwrap_spec=[object])
        def func(interp, w_ignored):
            return const
    make_func(const)
        
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

@expose_primitive(PRIMITIVE_BLOCK_COPY, unwrap_spec=[object, object])
def func(interp, w_context, w_argcnt):
    frame = interp.w_active_context
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

def finalize_block_ctx(interp, w_block_ctx, frame):
    # Set some fields
    w_block_ctx.pc = w_block_ctx.initialip
    w_block_ctx.w_sender = frame
    interp.w_active_context = w_block_ctx
    
@expose_primitive(PRIMITIVE_VALUE)
def func(interp, argument_count):
    # argument_count does NOT include the receiver.
    # This means that for argument_count == 3 the stack looks like:
    #  3      2       1      Top
    #  Rcvr | Arg 0 | Arg1 | Arg 2
    #
    
    frame = interp.w_active_context
    
    # Validate that we have a block on the stack and that it received
    # the proper number of arguments:
    w_block_ctx = frame.peek(argument_count)
    if not isinstance(w_block_ctx, model.W_BlockContext):
        raise PrimitiveFailedError()
    exp_arg_cnt = w_block_ctx.expected_argument_count()
    if argument_count != exp_arg_cnt: # exp_arg_cnt doesn't count self
        raise PrimitiveFailedError()

    # Initialize the block stack with the arguments that were
    # pushed.  Also pop the receiver.
    block_args = frame.pop_and_return_n(exp_arg_cnt)
    w_block_ctx.push_all(block_args)

    frame.pop()
    finalize_block_ctx(interp, w_block_ctx, frame)
    # Value is a special case of primitive which does not return
    # anything
    return None
    
    
@expose_primitive(PRIMITIVE_VALUE_WITH_ARGS, unwrap_spec=[object, object])
def func(interp, w_block_ctx, w_args):
    if not isinstance(w_block_ctx, model.W_BlockContext):
        raise PrimitiveFailedError()
    exp_arg_cnt = w_block_ctx.expected_argument_count()

    # Check that our arguments have pointers format and the right size:
    if w_args.getclass() != classtable.w_Array:
        raise PrimitiveFailedError()
    if w_args.size() != exp_arg_cnt:
        raise PrimitiveFailedError()
    
    # Push all the items from the array
    for i in range(exp_arg_cnt):
        w_block_ctx.push(w_args.fetchvarpointer(i))

    # XXX Check original logic. Image does not test this anyway
    # because falls back to value + internal implementation

    finalize_block_ctx(interp, w_block_ctx, interp.w_active_context)

    # Value: is a special case of primitive which does not return
    # anything
    return None

@expose_primitive(PRIMITIVE_PERFORM)
def func(interp, argcount):
    raise PrimitiveFailedError()

@expose_primitive(PRIMITIVE_PERFORM_WITH_ARGS,
                  unwrap_spec=[object, str, object])
def func(interp, w_rcvr, sel, w_args):
    w_method = w_rcvr.shadow_of_my_class().lookup(sel)
    assert w_method

    w_frame = w_method.create_frame(w_rcvr,
        [w_args.fetch(i) for i in range(w_args.size())])

    w_frame.w_sender = interp.w_active_context
    interp.w_active_context = w_frame

    # Don't put anything on the stack
    return None

@expose_primitive(PRIMITIVE_SIGNAL, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()
    
@expose_primitive(PRIMITIVE_WAIT, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()
    
@expose_primitive(PRIMITIVE_RESUME, unwrap_spec=[object])
def func(interp, w_rcvr,):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(PRIMITIVE_SUSPEND, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(PRIMITIVE_FLUSH_CACHE, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

# ___________________________________________________________________________
# PrimitiveLoadInstVar
#
# These are some wacky bytecodes in squeak.  They are defined to do
# the following:
#   primitiveLoadInstVar
#     | thisReceiver |
#     thisReceiver := self popStack.
#     self push: (self fetchPointer: primitiveIndex-264 ofObject: thisReceiver)

for i in range(264, 520):
    def make_prim(i):
        @expose_primitive(i, unwrap_spec=[object])
        def func(interp, w_object):
            return w_object.fetch(i - 264)
    globals()["INST_VAR_AT_%d" % (i-264)] = i
    make_prim(i)
    
