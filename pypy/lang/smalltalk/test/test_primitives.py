import py
import math
from pypy.lang.smalltalk.primitives import prim_table, PrimitiveFailedError
from pypy.lang.smalltalk import model, shadow
from pypy.lang.smalltalk import interpreter
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import objtable
from pypy.rlib.rarithmetic import INFINITY, NAN, isinf, isnan

# Violates the guideline, but we use it A LOT to reference the primitive codes:
import pypy.lang.smalltalk.primitives as p

mockclass = classtable.bootstrap_class

class MockFrame(interpreter.W_MethodContext):
    def __init__(self, stack):
        self.stack = stack

def wrap(x):
    if isinstance(x, int): return objtable.wrap_int(x)
    if isinstance(x, float): return objtable.wrap_float(x)
    if isinstance(x, model.W_Object): return x
    if isinstance(x, str) and len(x) == 1: return objtable.wrap_char(x)
    if isinstance(x, str): return objtable.wrap_string(x)
    raise NotImplementedError
    
def mock(stack):
    mapped_stack = [wrap(x) for x in stack]
    frame = MockFrame(mapped_stack)
    interp = interpreter.Interpreter()
    interp.w_active_context = frame
    return p.Args(interp, len(stack))

def prim(code, stack):
    args = mock(stack)
    res = prim_table[code](args)
    assert not len(args.interp.w_active_context.stack) # check args are consumed
    return res

def prim_fails(code, stack):
    args = mock(stack)
    orig_stack = list(args.interp.w_active_context.stack)
    try:
        prim_table[code](args)
        py.test.fail("Expected PrimitiveFailedError")
    except PrimitiveFailedError:
        assert args.interp.w_active_context.stack == orig_stack
        
# smallinteger tests
def test_small_int_add():
    assert prim(p.ADD, [1,2]).value == 3
    assert prim(p.ADD, [3,4]).value == 7

def test_small_int_add_fail():
    prim_fails(p.ADD, [1073741823,2])

def test_small_int_minus():
    assert prim(p.SUBTRACT, [5,9]).value == -4

def test_small_int_minus_fail():
    prim_fails(p.SUBTRACT, [-1073741823,2])
    
def test_small_int_divide():
    assert prim(p.DIVIDE, [6,3]).value == 2
    
def test_small_int_divide_fail():
    prim_fails(p.DIVIDE, [12, 0])
    prim_fails(p.DIVIDE, [12, 7])
    
def test_small_int_mod():
    assert prim(p.MOD, [12,7]).value == 5

def test_small_int_mod_fail():
    prim_fails(p.MOD, [12, 0])
    
def test_small_int_div():
    assert prim(p.DIV, [12,3]).value == 4
    assert prim(p.DIV, [12,7]).value == 1

def test_small_int_div_fail():
    prim_fails(p.DIV, [12, 0])
    
def test_small_int_quo():
    assert prim(p.QUO, [12,3]).value == 4
    assert prim(p.QUO, [12,7]).value == 1

def test_small_int_quo_fail():
    prim_fails(p.QUO, [12, 0])
    
def test_small_int_bit_and():
    assert prim(p.BIT_AND, [2, 4]).value == 0
    assert prim(p.BIT_AND, [2, 3]).value == 2
    assert prim(p.BIT_AND, [3, 4]).value == 0
    assert prim(p.BIT_AND, [4, 4]).value == 4
    
def test_small_int_bit_or():
    assert prim(p.BIT_OR, [2, 4]).value == 6
    assert prim(p.BIT_OR, [2, 3]).value == 3
    assert prim(p.BIT_OR, [3, 4]).value == 7
    assert prim(p.BIT_OR, [4, 4]).value == 4

def test_small_int_bit_xor():
    assert prim(p.BIT_XOR, [2, 4]).value == 6
    assert prim(p.BIT_XOR, [2, 3]).value == 1
    assert prim(p.BIT_XOR, [3, 4]).value == 7
    assert prim(p.BIT_XOR, [4, 4]).value == 0

def test_small_int_bit_shift():
    assert prim(p.BIT_SHIFT, [0, -3]).value == 0
    assert prim(p.BIT_SHIFT, [0, -2]).value == 0
    assert prim(p.BIT_SHIFT, [0, -1]).value == 0
    assert prim(p.BIT_SHIFT, [0, 0]).value == 0
    assert prim(p.BIT_SHIFT, [0, 1]).value == 0
    assert prim(p.BIT_SHIFT, [0, 2]).value == 0
    assert prim(p.BIT_SHIFT, [0, 3]).value == 0
    
def test_small_int_bit_shift_positive():
    assert prim(p.BIT_SHIFT, [4, -3]).value == 0
    assert prim(p.BIT_SHIFT, [4, -2]).value == 1
    assert prim(p.BIT_SHIFT, [4, -1]).value == 2
    assert prim(p.BIT_SHIFT, [4, 0]).value == 4
    assert prim(p.BIT_SHIFT, [4, 1]).value == 8
    assert prim(p.BIT_SHIFT, [4, 2]).value == 16
    assert prim(p.BIT_SHIFT, [4, 3]).value == 32
    assert prim(p.BIT_SHIFT, [4, 27]).value == 536870912
    
def test_small_int_bit_shift_negative():
    assert prim(p.BIT_SHIFT, [-4, -3]).value == -1
    assert prim(p.BIT_SHIFT, [-4, -2]).value == -1
    assert prim(p.BIT_SHIFT, [-4, -1]).value == -2
    assert prim(p.BIT_SHIFT, [-4, 0]).value == -4
    assert prim(p.BIT_SHIFT, [-4, 1]).value == -8
    assert prim(p.BIT_SHIFT, [-4, 2]).value == -16
    assert prim(p.BIT_SHIFT, [-4, 3]).value == -32
    assert prim(p.BIT_SHIFT, [-4, 27]).value == -536870912
    
def test_small_int_bit_shift_fail():
    prim_fails(p.BIT_SHIFT, [4, 32])
    prim_fails(p.BIT_SHIFT, [4, 31])
    prim_fails(p.BIT_SHIFT, [4, 30])
    prim_fails(p.BIT_SHIFT, [4, 29])
    prim_fails(p.BIT_SHIFT, [4, 28])

def test_float_add():
    assert prim(p.FLOAT_ADD, [1.0,2.0]).value == 3.0
    assert prim(p.FLOAT_ADD, [3.0,4.5]).value == 7.5

def test_float_subtract():
    assert prim(p.FLOAT_SUBTRACT, [1.0,2.0]).value == -1.0
    assert prim(p.FLOAT_SUBTRACT, [15.0,4.5]).value == 10.5

def test_float_multiply():
    assert prim(p.FLOAT_MULTIPLY, [10.0,2.0]).value == 20.0
    assert prim(p.FLOAT_MULTIPLY, [3.0,4.5]).value == 13.5

def test_float_divide():
    assert prim(p.FLOAT_DIVIDE, [1.0,2.0]).value == 0.5
    assert prim(p.FLOAT_DIVIDE, [3.5,4.0]).value == 0.875

def test_float_truncate():
    assert prim(p.FLOAT_TRUNCATED, [-4.6]).value == -4
    assert prim(p.FLOAT_TRUNCATED, [-4.5]).value == -4
    assert prim(p.FLOAT_TRUNCATED, [-4.4]).value == -4
    assert prim(p.FLOAT_TRUNCATED, [4.4]).value == 4
    assert prim(p.FLOAT_TRUNCATED, [4.5]).value == 4
    assert prim(p.FLOAT_TRUNCATED, [4.6]).value == 4


def test_at():
    w_obj = mockclass(0, varsized=True).as_class_get_shadow().new(1)
    w_obj.store(0, "foo")
    assert prim(p.AT, [w_obj, 0]) == "foo"

def test_invalid_at():
    w_obj = mockclass(0).as_class_get_shadow().new()
    prim_fails(p.AT, [w_obj, 0])

def test_at_put():
    w_obj = mockclass(0, varsized=1).as_class_get_shadow().new(1)
    assert prim(p.AT_PUT, [w_obj, 0, 22]).value == 22
    assert prim(p.AT, [w_obj, 0]).value == 22
    
def test_invalid_at_put():
    w_obj = mockclass(0).as_class_get_shadow().new()
    prim_fails(p.AT_PUT, [w_obj, 0, 22])

def test_string_at():
    assert prim(p.STRING_AT, ["foobar", 3]) == wrap("b")

def test_string_at_put():
    test_str = wrap("foobar")
    assert prim(p.STRING_AT_PUT, [test_str, 3, "c"]) == wrap("c")
    exp = "foocar"
    for i in range(len(exp)):
        assert prim(p.STRING_AT, [test_str, i]) == wrap(exp[i])

def test_object_at():
    w_v = prim(p.OBJECT_AT, ["q", objtable.CHARACTER_VALUE_INDEX])
    assert w_v.value == ord("q")

def test_invalid_object_at():
    prim_fails(p.OBJECT_AT, ["q", objtable.CHARACTER_VALUE_INDEX+1])
    
def test_object_at_put():
    w_obj = mockclass(1).as_class_get_shadow().new()
    assert prim(p.OBJECT_AT_PUT, [w_obj, 0, "q"]) is wrap("q")
    assert prim(p.OBJECT_AT, [w_obj, 0]) is wrap("q")

def test_invalid_object_at_put():
    w_obj = mockclass(1).as_class_get_shadow().new()
    prim_fails(p.OBJECT_AT, [w_obj, 1, 1])
    
def test_string_at_put():
    test_str = wrap("foobar")
    assert prim(p.STRING_AT_PUT, [test_str, 3, "c"]) == wrap("c")
    exp = "foocar"
    for i in range(len(exp)):
        assert prim(p.STRING_AT, [test_str, i]) == wrap(exp[i])

def test_new():
    w_Object = classtable.classtable['w_Object']
    w_res = prim(p.NEW, [w_Object])
    assert w_res.getclass() is w_Object
    
def test_invalid_new():
    prim_fails(p.NEW, [classtable.w_String])

def test_new_with_arg():
    w_res = prim(p.NEW_WITH_ARG, [classtable.w_String, 20])
    assert w_res.getclass() == classtable.w_String
    assert w_res.size() == 20    

def test_invalid_new_with_arg():
    w_Object = classtable.classtable['w_Object']
    prim_fails(p.NEW_WITH_ARG, [w_Object, 20])
    
def test_inst_var_at():
    # I am not entirely sure if this is what this primitive is
    # supposed to do, so the test may be bogus:
    w_v = prim(p.INST_VAR_AT, ["q", objtable.CHARACTER_VALUE_INDEX])
    assert w_v.value == ord("q")
    w_v = prim(p.INST_VAR_AT, ["abc", 1])
    assert w_v.value == ord("b")

def test_as_oop():
    w_obj = mockclass(0).as_class_get_shadow().new()
    w_obj.w_hash = wrap(22)
    assert prim(p.AS_OOP, [w_obj]).value == 22

def test_as_oop_not_applicable_to_int():
    prim_fails(p.AS_OOP, [22])

def test_const_primitives():
    for (code, const) in [
        (p.PUSH_TRUE, objtable.w_true),
        (p.PUSH_FALSE, objtable.w_false),
        (p.PUSH_NIL, objtable.w_nil),
        (p.PUSH_MINUS_ONE, objtable.w_mone),
        (p.PUSH_ZERO, objtable.w_zero),
        (p.PUSH_ONE, objtable.w_one),
        (p.PUSH_TWO, objtable.w_two),
        ]:
        assert prim(code, [objtable.w_nil]) is const
    assert prim(p.PUSH_SELF, [objtable.w_nil]) is objtable.w_nil
    assert prim(p.PUSH_SELF, ["a"]) is wrap("a")

def test_boolean():
    assert prim(p.LESSTHAN, [1,2]) == objtable.w_true
    assert prim(p.GREATERTHAN, [3,4]) == objtable.w_false
    assert prim(p.LESSOREQUAL, [1,2]) == objtable.w_true
    assert prim(p.GREATEROREQUAL, [3,4]) == objtable.w_false
    assert prim(p.EQUAL, [2,2]) == objtable.w_true
    assert prim(p.NOTEQUAL, [2,2]) == objtable.w_false

def test_float_boolean():
    assert prim(p.FLOAT_LESSTHAN, [1.0,2.0]) == objtable.w_true
    assert prim(p.FLOAT_GREATERTHAN, [3.0,4.0]) == objtable.w_false
    assert prim(p.FLOAT_LESSOREQUAL, [1.3,2.6]) == objtable.w_true
    assert prim(p.FLOAT_GREATEROREQUAL, [3.5,4.9]) == objtable.w_false
    assert prim(p.FLOAT_EQUAL, [2.2,2.2]) == objtable.w_true
    assert prim(p.FLOAT_NOTEQUAL, [2.2,2.2]) == objtable.w_false
    
def test_block_copy_and_value():
    # see test_interpreter for tests of these opcodes
    return

ROUNDING_DIGITS = 8

def float_equals(w_f,f):
    return round(w_f.value,ROUNDING_DIGITS) == round(f,ROUNDING_DIGITS)

def test_primitive_square_root():
    assert prim(p.FLOAT_SQUARE_ROOT, [4.0]).value == 2.0
    assert float_equals(prim(p.FLOAT_SQUARE_ROOT, [2.0]), math.sqrt(2))
    prim_fails(p.FLOAT_SQUARE_ROOT, [-2.0])

def test_primitive_sin():
    assert prim(p.FLOAT_SIN, [0.0]).value == 0.0
    assert float_equals(prim(p.FLOAT_SIN, [math.pi]), 0.0)
    assert float_equals(prim(p.FLOAT_SIN, [math.pi/2]), 1.0)

def test_primitive_arctan():
    assert prim(p.FLOAT_ARCTAN, [0.0]).value == 0.0
    assert float_equals(prim(p.FLOAT_ARCTAN, [1]), math.pi/4)
    assert float_equals(prim(p.FLOAT_ARCTAN, [1e99]), math.pi/2)

def test_primitive_log_n():
    assert prim(p.FLOAT_LOG_N, [1.0]).value == 0.0
    assert prim(p.FLOAT_LOG_N, [math.e]).value == 1.0
    assert float_equals(prim(p.FLOAT_LOG_N, [10.0]), math.log(10))
    assert isinf(prim(p.FLOAT_LOG_N, [0.0]).value) # works also for negative infinity
    assert isnan(prim(p.FLOAT_LOG_N, [-1.0]).value)

def test_primitive_exp():
    assert float_equals(prim(p.FLOAT_EXP, [-1.0]), 1/math.e)
    assert prim(p.FLOAT_EXP, [0]).value == 1
    assert float_equals(prim(p.FLOAT_EXP, [1]), math.e)
    assert float_equals(prim(p.FLOAT_EXP, [math.log(10)]), 10)

def equals_ttp(rcvr,arg,res):
    return float_equals(prim(p.FLOAT_TIMES_TWO_POWER, [rcvr,arg]), res)

def test_times_two_power():
    assert equals_ttp(1,1,2)
    assert equals_ttp(1.5,1,3)
    assert equals_ttp(2,4,32)
    assert equals_ttp(0,2,0)
    assert equals_ttp(-1,2,-4)
    assert equals_ttp(1.5,0,1.5)
    assert equals_ttp(1.5,-1,0.75)

def test_full_gc():
    # Should not fail :-)
    prim(p.FULL_GC, [42]) # Dummy arg

