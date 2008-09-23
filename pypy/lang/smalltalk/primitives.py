import inspect
import math
import operator
from pypy.lang.smalltalk import model, shadow
from pypy.lang.smalltalk import constants
from pypy.lang.smalltalk.error import PrimitiveFailedError, \
    PrimitiveNotYetWrittenError
from pypy.rlib import rarithmetic, unroll
from pypy.lang.smalltalk import wrapper


def assert_bounds(n0, minimum, maximum):
    if not minimum <= n0 < maximum:
        raise PrimitiveFailedError()

def assert_valid_index(space, n0, w_obj):
    if not 0 <= n0 < w_obj.primsize(space):
        raise PrimitiveFailedError()
    # return the index, since from here on the annotator knows that
    # n0 cannot be negative
    return n0

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
# clean up namespace:
del i
prim_table_implemented_only = []

# indicates that what is pushed is an index1, but it is unwrapped and
# converted to an index0 
index1_0 = object()
char = object()

def expose_primitive(code, unwrap_spec=None, no_result=False):
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
            def wrapped(interp, argument_count_m1):
                w_result = func(interp, argument_count_m1)
                if not no_result:
                    assert w_result is not None
                    interp.s_active_context().push(w_result)
                return w_result
        else:
            len_unwrap_spec = len(unwrap_spec)
            assert (len_unwrap_spec == len(inspect.getargspec(func)[0]) + 1,
                    "wrong number of arguments")
            unrolling_unwrap_spec = unrolling_iterable(enumerate(unwrap_spec))
            def wrapped(interp, argument_count_m1):
                argument_count = argument_count_m1 + 1 # to account for the rcvr
                frame = interp.w_active_context()
                s_frame = frame.as_context_get_shadow(interp.space)
                assert argument_count == len_unwrap_spec
                if len(s_frame.stack()) < len_unwrap_spec:
                    raise PrimitiveFailedError()
                args = ()
                for i, spec in unrolling_unwrap_spec:
                    index = len_unwrap_spec - 1 - i
                    w_arg = s_frame.peek(index)
                    if spec is int:
                        args += (interp.space.unwrap_int(w_arg), )
                    elif spec is index1_0:
                        args += (interp.space.unwrap_int(w_arg)-1, )
                    elif spec is float:
                        args += (interp.space.unwrap_float(w_arg), )
                    elif spec is object:
                        args += (w_arg, )
                    elif spec is str:
                        assert isinstance(w_arg, model.W_BytesObject)
                        args += (w_arg.as_string(), )
                    elif spec is char:
                        args += (unwrap_char(w_arg), )
                    else:
                        raise NotImplementedError(
                            "unknown unwrap_spec %s" % (spec, ))
                w_result = func(interp, *args)
                # After calling primitive, reload context-shadow in case it
                # needs to be updated
                new_s_frame = interp.s_active_context()
                frame.as_context_get_shadow(interp.space).pop_n(len_unwrap_spec)   # only if no exception occurs!
                if not no_result:
                    assert w_result is not None
                    new_s_frame.push(w_result)
        wrapped.func_name = "wrap_prim_" + name
        prim_table[code] = wrapped
        prim_table_implemented_only.append((code, wrapped))
        return func
    return decorator

# ___________________________________________________________________________
# SmallInteger Primitives


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
            return interp.space.wrap_int(res)
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
            return interp.space.wrap_int(res)
    make_func(op)

# #/ -- return the result of a division, only succeed if the division is exact
@expose_primitive(DIVIDE, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    if receiver % argument != 0:
        raise PrimitiveFailedError()
    return interp.space.wrap_int(receiver // argument)

# #\\ -- return the remainder of a division
@expose_primitive(MOD, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    return interp.space.wrap_int(receiver % argument)

# #// -- return the result of a division, rounded towards negative zero
@expose_primitive(DIV, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    return interp.space.wrap_int(receiver // argument)
    
# #// -- return the result of a division, rounded towards negative infinity
@expose_primitive(QUO, unwrap_spec=[int, int])
def func(interp, receiver, argument):
    if argument == 0:
        raise PrimitiveFailedError()
    return interp.space.wrap_int(receiver // argument)
    
# #bitShift: -- return the shifted value
@expose_primitive(BIT_SHIFT, unwrap_spec=[int, int])
def func(interp, receiver, argument):

    # left shift, must fail if we loose bits beyond 32
    if argument > 0:
        shifted = receiver << argument
        if (shifted >> argument) != receiver:
            raise PrimitiveFailedError()
        return interp.space.wrap_int(shifted)
            
    # right shift, ok to lose bits
    else:
        return interp.space.wrap_int(receiver >> -argument)
   

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
            w_res = interp.space.wrap_float(op(v1, v2))
            return w_res
    make_func(op)

@expose_primitive(FLOAT_TRUNCATED, unwrap_spec=[float])
def func(interp, f): 
    w_res = interp.space.wrap_int(int(f))
    return w_res

@expose_primitive(FLOAT_TIMES_TWO_POWER, unwrap_spec=[float, int])
def func(interp, rcvr, arg): 
    w_res = interp.space.wrap_float(math.ldexp(rcvr, arg))
    return w_res

@expose_primitive(FLOAT_SQUARE_ROOT, unwrap_spec=[float])
def func(interp, f): 
    if f < 0.0:
        raise PrimitiveFailedError
    w_res = interp.space.wrap_float(math.sqrt(f))
    return w_res

@expose_primitive(FLOAT_SIN, unwrap_spec=[float])
def func(interp, f): 
    w_res = interp.space.wrap_float(math.sin(f))
    return w_res

@expose_primitive(FLOAT_ARCTAN, unwrap_spec=[float])
def func(interp, f): 
    w_res = interp.space.wrap_float(math.atan(f))
    return w_res

@expose_primitive(FLOAT_LOG_N, unwrap_spec=[float])
def func(interp, f): 
    if f == 0:
        res = -rarithmetic.INFINITY
    elif f < 0:
        res = rarithmetic.NAN
    else:
        res = math.log(f)
    return interp.space.wrap_float(res)

@expose_primitive(FLOAT_EXP, unwrap_spec=[float])
def func(interp, f): 
    w_res = interp.space.wrap_float(math.exp(f))
    return w_res

MAKE_POINT = 18

@expose_primitive(MAKE_POINT, unwrap_spec=[int, int])
def func(interp, x, y):
    w_res = interp.space.classtable['w_Point'].as_class_get_shadow(interp.space).new(2)
    point = wrapper.PointWrapper(interp.space, w_res)
    point.store_x(interp.space, x)
    point.store_y(interp.space, y)
    return w_res


# ___________________________________________________________________________
# Failure

FAIL = 19

# ___________________________________________________________________________
# Subscript and Stream Primitives

AT = 60
AT_PUT = 61
SIZE = 62
STRING_AT = 63
STRING_AT_PUT = 64

@expose_primitive(AT, unwrap_spec=[object, index1_0])
def func(interp, w_obj, n0):
    n0 = assert_valid_index(interp.space, n0, w_obj)
    return w_obj.at0(interp.space, n0)

@expose_primitive(AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_obj, n0, w_val):
    n0 = assert_valid_index(interp.space, n0, w_obj)
    w_obj.atput0(interp.space, n0, w_val)
    return w_val

@expose_primitive(SIZE, unwrap_spec=[object])
def func(interp, w_obj):
    if not w_obj.shadow_of_my_class(interp.space).isvariable():
        raise PrimitiveFailedError()
    return interp.space.wrap_int(w_obj.primsize(interp.space))

@expose_primitive(STRING_AT, unwrap_spec=[object, index1_0])
def func(interp, w_obj, n0):
    n0 = assert_valid_index(interp.space, n0, w_obj)
    # XXX I am not sure this is correct, but it un-breaks translation:
    # make sure that getbyte is only performed on W_BytesObjects
    if not isinstance(w_obj, model.W_BytesObject):
        raise PrimitiveFailedError
    return interp.space.wrap_char(w_obj.getchar(n0))

@expose_primitive(STRING_AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_obj, n0, w_val):
    val = interp.space.unwrap_char(w_val)
    n0 = assert_valid_index(interp.space, n0, w_obj)
    if not (isinstance(w_obj, model.W_CompiledMethod) or
            isinstance(w_obj, model.W_BytesObject)):
        raise PrimitiveFailedError()
    w_obj.setchar(n0, val)
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
    return w_rcvr.literalat0(interp.space, n0)

@expose_primitive(OBJECT_AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_rcvr, n0, w_value):
    if not isinstance(w_rcvr, model.W_CompiledMethod):
        raise PrimitiveFailedError()
    #assert_bounds(n0, 0, len(w_rcvr.literals))
    w_rcvr.literalatput0(interp.space, n0, w_value)
    return w_value

@expose_primitive(NEW, unwrap_spec=[object])
def func(interp, w_cls):
    assert isinstance(w_cls, model.W_PointersObject)
    s_class = w_cls.as_class_get_shadow(interp.space)
    if s_class.isvariable():
        raise PrimitiveFailedError()
    return s_class.new()

@expose_primitive(NEW_WITH_ARG, unwrap_spec=[object, int])
def func(interp, w_cls, size):
    assert isinstance(w_cls, model.W_PointersObject)
    s_class = w_cls.as_class_get_shadow(interp.space)
    if not s_class.isvariable():
        raise PrimitiveFailedError()
    return s_class.new(size)

@expose_primitive(ARRAY_BECOME_ONE_WAY, unwrap_spec=[object, object])
def func(interp, w_obj1, w_obj2):
    raise PrimitiveNotYetWrittenError

@expose_primitive(INST_VAR_AT, unwrap_spec=[object, index1_0])
def func(interp, w_rcvr, n0):
    "Fetches a fixed field from the object, and fails otherwise"
    s_class = w_rcvr.shadow_of_my_class(interp.space)
    assert_bounds(n0, 0, s_class.instsize())
    # only pointers have non-0 size
    # XXX Now MethodContext is still own format, leave
    #assert isinstance(w_rcvr, model.W_PointersObject)
    return w_rcvr.fetch(interp.space, n0)

@expose_primitive(INST_VAR_AT_PUT, unwrap_spec=[object, index1_0, object])
def func(interp, w_rcvr, n0, w_value):
    "Stores a value into a fixed field from the object, and fails otherwise"
    s_class = w_rcvr.shadow_of_my_class(interp.space)
    assert_bounds(n0, 0, s_class.instsize())
    # XXX Now MethodContext is still own format, leave
    #assert isinstance(w_rcvr, model.W_PointersObject)
    w_rcvr.store(interp.space, n0, w_value)
    return w_value

@expose_primitive(AS_OOP, unwrap_spec=[object])
def func(interp, w_rcvr):
    if isinstance(w_rcvr, model.W_SmallInteger):
        raise PrimitiveFailedError()
    return interp.space.wrap_int(w_rcvr.gethash())

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

@expose_primitive(NEW_METHOD, unwrap_spec=[object, int, int])
def func(interp, w_class, bytecount, header):
    # We ignore w_class because W_CompiledMethod is special
    w_method = model.W_CompiledMethod(bytecount, header)
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
    return interp.space.wrap_bool(w_arg.is_same_object(w_rcvr))

@expose_primitive(CLASS, unwrap_spec=[object])
def func(interp, w_obj):
    return w_obj.getclass(interp.space)

@expose_primitive(BYTES_LEFT, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(QUIT, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(EXIT_TO_DEBUGGER, unwrap_spec=[object])
def func(interp, w_rcvr):
    raise PrimitiveNotYetWrittenError()

@expose_primitive(CHANGE_CLASS, unwrap_spec=[object, object], no_result=True)
def func(interp, w_arg, w_rcvr):
    w_arg_class = w_arg.getclass(interp.space)
    w_rcvr_class = w_rcvr.getclass(interp.space)

    # We should fail if:

    # 1. Rcvr or arg are SmallIntegers
    # XXX this is wrong too
    if (w_arg_class.is_same_object(interp.space.w_SmallInteger) or
        w_rcvr_class.is_same_object(interp.space.w_SmallInteger)):
        raise PrimitiveFailedError()

    # 2. Rcvr is an instance of a compact class and argument isn't
    # or vice versa XXX we don't have to fail here, but for squeak it's a problem

    # 3. Format of rcvr is different from format of argument
    raise PrimitiveNotYetWrittenError()     # XXX needs to work in the shadows
    if w_arg_class.format != w_rcvr_class.format:
        raise PrimitiveFailedError()

    # Fail when argument class is fixed and rcvr's size differs from the
    # size of an instance of the arg
    if w_arg_class.instsize() != w_rcvr_class.instsize():
        raise PrimitiveFailedError()

    w_rcvr.w_class = w_arg.w_class

# ___________________________________________________________________________
# Squeak Miscellaneous Primitives (128-149)
BECOME = 128
FULL_GC = 130
INC_GC = 131

@expose_primitive(BECOME, unwrap_spec=[object, object])
def func(interp, w_rcvr, w_new):
    if w_rcvr.size() != w_new.size():
        raise PrimitiveFailedError
    w_lefts = []
    w_rights = []
    for i in range(w_rcvr.size()):
        w_left = w_rcvr.at0(interp.space, i)
        w_right = w_new.at0(interp.space, i)
        if w_left.become(w_right):
            w_lefts.append(w_left)
            w_rights.append(w_right)
        else:
            for i in range(len(w_lefts)):
                w_lefts[i].become(w_rights[i])
            raise PrimitiveFailedError()
    return w_rcvr

def fake_bytes_left(interp):
    return interp.space.wrap_int(2**20) # XXX we don't know how to do this :-(

@expose_primitive(INC_GC, unwrap_spec=[object])
@expose_primitive(FULL_GC, unwrap_spec=[object])
def func(interp, w_arg): # Squeak pops the arg and ignores it ... go figure
    from pypy.rlib import rgc
    rgc.collect()
    return fake_bytes_left(interp)

#____________________________________________________________________________
# Time Primitives
MILLISECOND_CLOCK = 135
SECONDS_CLOCK = 137

@expose_primitive(MILLISECOND_CLOCK, unwrap_spec=[object])
def func(interp, w_arg):
    import time
    import math
    return interp.space.wrap_int(int(math.fmod(time.time()*1000, constants.TAGGED_MAXINT/2)))

@expose_primitive(SECONDS_CLOCK, unwrap_spec=[object])
def func(interp, w_arg):
    import time
    return interp.space.wrap_int(0x23910d6c)      # HACK: too big for a small int!
    #return interp.space.wrap_int(int(time.time()))

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
            w_res = interp.space.wrap_bool(res)
            return w_res
    make_func(op)

for (code,op) in bool_ops.items():
    def make_func(op):
        @expose_primitive(code+_FLOAT_OFFSET, unwrap_spec=[float, float])
        def func(interp, v1, v2):
            res = op(v1, v2)
            w_res = interp.space.wrap_bool(res)
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

def make_push_const_func(code, name):
    @expose_primitive(code, unwrap_spec=[object])
    def func(interp, w_ignored):
        return getattr(interp.space, name)

for (code, name) in [
    (PUSH_TRUE, "w_true"),
    (PUSH_FALSE, "w_false"),
    (PUSH_NIL, "w_nil"),
    (PUSH_MINUS_ONE, "w_minus_one"),
    (PUSH_ZERO, "w_zero"),
    (PUSH_ONE, "w_one"),
    (PUSH_TWO, "w_two"),
    ]:
    make_push_const_func(code, name)
        
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

@expose_primitive(PRIMITIVE_BLOCK_COPY, unwrap_spec=[object, int])
def func(interp, w_context, argcnt):
    frame = interp.s_active_context()

    # From B.B.: If receiver is a MethodContext, then it becomes
    # the new BlockContext's home context.  Otherwise, the home
    # context of the receiver is used for the new BlockContext.
    # Note that in our impl, MethodContext.w_home == self
    assert isinstance(w_context, model.W_PointersObject)
    w_method_context = w_context.as_context_get_shadow(interp.space).w_home()

    # The block bytecodes are stored inline: so we skip past the
    # byteodes to invoke this primitive to find them (hence +2)
    initialip = frame.pc() + 2
    w_new_context = shadow.BlockContextShadow.make_context(
        interp.space,
        w_method_context, interp.space.w_nil, argcnt, initialip)
    return w_new_context

def finalize_block_ctx(interp, s_block_ctx, frame):
    # Set some fields
    s_block_ctx.store_pc(s_block_ctx.initialip())
    s_block_ctx.store_w_sender(frame)
    interp.store_w_active_context(s_block_ctx.w_self())
    
@expose_primitive(PRIMITIVE_VALUE, no_result=True)
def func(interp, argument_count):
    # argument_count does NOT include the receiver.
    # This means that for argument_count == 3 the stack looks like:
    #  3      2       1      Top
    #  Rcvr | Arg 0 | Arg1 | Arg 2
    #
    
    frame = interp.s_active_context()
    
    # Validate that we have a block on the stack and that it received
    # the proper number of arguments:
    w_block_ctx = frame.peek(argument_count)

    # XXX need to check this since VALUE is called on all sorts of objects.
    if not w_block_ctx.getclass(interp.space).is_same_object(
        interp.space.w_BlockContext):
        raise PrimitiveFailedError()
    
    assert isinstance(w_block_ctx, model.W_PointersObject)

    s_block_ctx = w_block_ctx.as_blockcontext_get_shadow(interp.space)

    exp_arg_cnt = s_block_ctx.expected_argument_count()
    if argument_count != exp_arg_cnt: # exp_arg_cnt doesn't count self
        raise PrimitiveFailedError()

    # Initialize the block stack with the arguments that were
    # pushed.  Also pop the receiver.
    block_args = frame.pop_and_return_n(exp_arg_cnt)

    # Reset stack of blockcontext to []
    s_block_ctx.reset_stack()
    s_block_ctx.push_all(block_args)

    frame.pop()
    finalize_block_ctx(interp, s_block_ctx, frame.w_self())
    
@expose_primitive(PRIMITIVE_VALUE_WITH_ARGS, unwrap_spec=[object, object],
                  no_result=True)
def func(interp, w_block_ctx, w_args):

    assert isinstance(w_block_ctx, model.W_PointersObject)
    s_block_ctx = w_block_ctx.as_blockcontext_get_shadow(interp.space)
    exp_arg_cnt = s_block_ctx.expected_argument_count()

    # Check that our arguments have pointers format and the right size:
    if not w_args.getclass(interp.space).is_same_object(
            interp.space.w_Array):
        raise PrimitiveFailedError()
    if w_args.size() != exp_arg_cnt:
        raise PrimitiveFailedError()
    
    assert isinstance(w_args, model.W_PointersObject)
    # Push all the items from the array
    for i in range(exp_arg_cnt):
        s_block_ctx.push(w_args.at0(interp.space, i))

    # XXX Check original logic. Image does not test this anyway
    # because falls back to value + internal implementation
    finalize_block_ctx(interp, s_block_ctx, interp.w_active_context())

@expose_primitive(PRIMITIVE_PERFORM)
def func(interp, argcount):
    raise PrimitiveFailedError()

@expose_primitive(PRIMITIVE_PERFORM_WITH_ARGS,
                  unwrap_spec=[object, str, object],
                  no_result=True)
def func(interp, w_rcvr, sel, w_args):
    w_method = w_rcvr.shadow_of_my_class(interp.space).lookup(sel)
    assert w_method

    w_frame = w_method.create_frame(interp.space, w_rcvr,
        [w_args.fetch(interp.space, i) for i in range(w_args.size())])

    w_frame.as_context_get_shadow(interp.space).store_w_sender(interp.w_active_context())
    interp.store_w_active_context(w_frame)

@expose_primitive(PRIMITIVE_SIGNAL, unwrap_spec=[object])
def func(interp, w_rcvr):
    # XXX we might want to disable this check
    if not w_rcvr.getclass(interp.space).is_same_object(
        interp.space.classtable['w_Semaphore']):
        raise PrimitiveFailedError()
    wrapper.SemaphoreWrapper(interp.space, w_rcvr).signal(interp)
    return w_rcvr
    
@expose_primitive(PRIMITIVE_WAIT, unwrap_spec=[object])
def func(interp, w_rcvr):
    # XXX we might want to disable this check
    if not w_rcvr.getclass(interp.space).is_same_object(
        interp.space.classtable['w_Semaphore']):
        raise PrimitiveFailedError()
    wrapper.SemaphoreWrapper(interp.space, w_rcvr).wait(interp)
    return w_rcvr
    
@expose_primitive(PRIMITIVE_RESUME, unwrap_spec=[object])
def func(interp, w_rcvr,):
    # XXX we might want to disable this check
    if not w_rcvr.getclass(interp.space).is_same_object(
        interp.space.classtable['w_Process']):
        raise PrimitiveFailedError()
    wrapper.ProcessWrapper(interp.space, w_rcvr).resume(interp)
    return w_rcvr
 
@expose_primitive(PRIMITIVE_SUSPEND, unwrap_spec=[object])
def func(interp, w_rcvr):
    # XXX we might want to disable this check
    if not w_rcvr.getclass(interp.space).is_same_object(
        interp.space.classtable['w_Process']):
        raise PrimitiveFailedError()
    wrapper.ProcessWrapper(interp.space, w_rcvr).suspend(interp)
    return w_rcvr
 
@expose_primitive(PRIMITIVE_FLUSH_CACHE, unwrap_spec=[object])
def func(interp, w_rcvr):
    # XXX we currently don't care about bad flushes :) XXX
    # raise PrimitiveNotYetWrittenError()
    return w_rcvr

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
            return w_object.fetch(interp.space, i - 264)
    globals()["INST_VAR_AT_%d" % (i-264)] = i
    make_prim(i)
    

unrolling_prim_table = unroll.unrolling_iterable(prim_table_implemented_only)
