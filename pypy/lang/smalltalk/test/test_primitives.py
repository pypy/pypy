import py
from pypy.lang.smalltalk.primitives import prim_table, PrimitiveFailedError
import pypy.lang.smalltalk.primitives as p
import pypy.lang.smalltalk.model as model
import pypy.lang.smalltalk.interpreter as interp
import pypy.lang.smalltalk.classtable as ct
import pypy.lang.smalltalk.fakeimage as fimg

class MockFrame(interp.W_ContextFrame):
    def __init__(self, stack):
        self.stack = stack

def wrap(x):
    if isinstance(x, int): return fimg.wrap_int(x)
    if isinstance(x, float): return fimg.wrap_float(x)
    if isinstance(x, model.W_Object): return x
    if isinstance(x, str) and len(x) == 1: return fimg.wrap_char(x)
    if isinstance(x, str): return fimg.wrap_string(x)
    raise NotImplementedError
    
def mock(stack):
    mapped_stack = [wrap(x) for x in stack]
    return MockFrame(mapped_stack)

def prim(code, stack):
    stack_w = mock(stack)
    res = prim_table[code](stack_w)
    assert not len(stack_w.stack)    # only pass as many arguments as it uses
    return res

def prim_fails(code, stack):
    stack_w = mock(stack)
    orig_stack = list(stack_w.stack)
    try:
        prim_table[code](stack_w)
        py.test.fail("Expected PrimitiveFailedError")
    except PrimitiveFailedError:
        assert stack_w.stack == orig_stack

def test_small_int_plus():
    assert prim(p.ADD, [1,2]).value == 3
    assert prim(p.ADD, [3,4]).value == 7

def test_small_int_minus():
    assert prim(p.SUBTRACT, [5,9]).value == -4

def test_small_int_overflow():
    prim_fails(p.ADD, [1073741823,2])
    
def test_float():
    assert prim(p.FLOAT_ADD, [1.0,2.0]).value == 3.0
    assert prim(p.FLOAT_ADD, [3,4.5]).value == 7.5

def test_at():
    w_obj = model.W_Class(None, None, 0, format=model.VAR_POINTERS).new(1)
    w_obj.setindexedvar(0, "foo")
    assert prim(p.AT, [w_obj, 0]) == "foo"

def test_invalid_at():
    w_obj = model.W_Class(None, None, 0, format=model.POINTERS).new()
    prim_fails(p.AT, [w_obj, 0])

def test_at_put():
    w_obj = model.W_Class(None, None, 0, format=model.VAR_POINTERS).new(1)
    assert prim(p.AT_PUT, [w_obj, 0, 22]).value == 22
    assert prim(p.AT, [w_obj, 0]).value == 22
    
def test_invalid_at_put():
    w_obj = model.W_Class(None, None, 0, format=model.POINTERS).new()
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
    w_v = prim(p.OBJECT_AT, ["q", fimg.CHARACTER_VALUE_INDEX])
    assert w_v.value == ord("q")

def test_invalid_object_at():
    prim_fails(p.OBJECT_AT, ["q", fimg.CHARACTER_VALUE_INDEX+1])
    
def test_object_at_put():
    w_obj = model.W_Class(None, None, 1, format=model.POINTERS).new()
    assert prim(p.OBJECT_AT_PUT, [w_obj, 0, "q"]) is wrap("q")
    assert prim(p.OBJECT_AT, [w_obj, 0]) is wrap("q")

def test_invalid_object_at_put():
    w_obj = model.W_Class(None, None, 1, format=model.POINTERS).new()
    prim_fails(p.OBJECT_AT, [w_obj, 1, 1])
    
def test_string_at_put():
    test_str = wrap("foobar")
    assert prim(p.STRING_AT_PUT, [test_str, 3, "c"]) == wrap("c")
    exp = "foocar"
    for i in range(len(exp)):
        assert prim(p.STRING_AT, [test_str, i]) == wrap(exp[i])

def test_new():
    w_res = prim(p.NEW, [ct.w_Object])
    assert w_res.w_class == ct.w_Object
    
def test_invalid_new():
    prim_fails(p.NEW, [ct.w_ByteString])

def test_new_with_arg():
    w_res = prim(p.NEW_WITH_ARG, [ct.w_ByteString, 20])
    assert w_res.w_class == ct.w_ByteString
    assert w_res.size() == 20    

def test_invalid_new_with_arg():
    prim_fails(p.NEW_WITH_ARG, [ct.w_Object, 20])
    
def test_inst_var_at():
    # I am not entirely sure if this is what this primitive is
    # supposed to do, so the test may be bogus:
    w_v = prim(p.INST_VAR_AT, ["q", fimg.CHARACTER_VALUE_INDEX])
    assert w_v.value == ord("q")
    w_v = prim(p.INST_VAR_AT, ["abc", 1])
    assert w_v.value == ord("b")

def test_as_oop():
    w_obj = model.W_Class(None, None, 0, format=model.POINTERS).new()
    w_obj.w_hash = wrap(22)
    assert prim(p.AS_OOP, [w_obj]).value == 22

def test_as_oop_not_applicable_to_int():
    prim_fails(p.AS_OOP, [22])

def test_const_primitives():
    for (code, const) in [
        (p.PUSH_TRUE, fimg.w_true),
        (p.PUSH_FALSE, fimg.w_false),
        (p.PUSH_NIL, fimg.w_nil),
        (p.PUSH_MINUS_ONE, fimg.w_mone),
        (p.PUSH_ZERO, fimg.w_zero),
        (p.PUSH_ONE, fimg.w_one),
        (p.PUSH_TWO, fimg.w_two),
        ]:
        assert prim(code, [fimg.w_nil]) is const
    assert prim(p.PUSH_SELF, [fimg.w_nil]) is fimg.w_nil
    assert prim(p.PUSH_SELF, ["a"]) is wrap("a")

def test_boolean():
    assert prim(p.LESSTHAN, [1,2]) == fimg.w_true
    assert prim(p.GREATERTHAN, [3,4]) == fimg.w_false
    assert prim(p.LESSOREQUAL, [1,2]) == fimg.w_true
    assert prim(p.GREATEROREQUAL, [3,4]) == fimg.w_false
    assert prim(p.EQUAL, [2,2]) == fimg.w_true
    assert prim(p.NOTEQUAL, [2,2]) == fimg.w_false

def test_float_boolean():
    assert prim(p.FLOAT_LESSTHAN, [1.0,2.0]) == fimg.w_true
    assert prim(p.FLOAT_GREATERTHAN, [3.0,4.0]) == fimg.w_false
    assert prim(p.FLOAT_LESSOREQUAL, [1.3,2.6]) == fimg.w_true
    assert prim(p.FLOAT_GREATEROREQUAL, [3.5,4.9]) == fimg.w_false
    assert prim(p.FLOAT_EQUAL, [2.2,2.2]) == fimg.w_true
    assert prim(p.FLOAT_NOTEQUAL, [2.2,2.2]) == fimg.w_false
