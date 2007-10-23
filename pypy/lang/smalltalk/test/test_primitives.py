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
    if isinstance(x, int): return fimg.small_int(x)
    if isinstance(x, float): return fimg.wrap_float(x)
    if isinstance(x, model.W_Object): return x
    raise NotImplementedError
    
def mock(stack):
    mapped_stack = [wrap(x) for x in stack]
    return MockFrame(mapped_stack)
        
def test_small_int_plus():
    assert prim_table[p.ADD](mock([1,2])).value == 3
    assert prim_table[p.ADD](mock([3,4])).value == 7

def test_small_int_minus():
    assert prim_table[p.SUBTRACT](mock([5,9])).value == -4

def test_small_int_overflow():
    def f():
        prim_table[p.ADD](mock([1073741823,2]))
    py.test.raises(PrimitiveFailedError, f)
    
def test_float():
    assert prim_table[p.FLOAT_ADD](mock([1.0,2.0])).value == 3.0
    assert prim_table[p.FLOAT_ADD](mock([3,4.5])).value == 7.5

def test_at():
    w_obj = model.W_Class(None, None, 0, format=model.VAR_POINTERS).new(1)
    w_obj.setindexedvar(0, "foo")
    assert prim_table[p.AT](mock([w_obj, 0])) == "foo"

def test_at_put():
    w_obj = model.W_Class(None, None, 0, format=model.VAR_POINTERS).new(1)
    assert prim_table[p.AT_PUT](mock([w_obj, 0, 22])).value == 22
    assert prim_table[p.AT](mock([w_obj, 0])).value == 22
    
def test_string_at():
    w_str = fimg.make_string("foobar")
    assert prim_table[p.STRING_AT](mock([w_str, 3])) == \
           fimg.make_char("b")

def test_boolean():
    assert prim_table[p.LESSTHAN](mock([1,2])) == fimg.w_true
    assert prim_table[p.GREATERTHAN](mock([3,4])) == fimg.w_false
    assert prim_table[p.LESSOREQUAL](mock([1,2])) == fimg.w_true
    assert prim_table[p.GREATEROREQUAL](mock([3,4])) == fimg.w_false
    assert prim_table[p.EQUAL](mock([2,2])) == fimg.w_true
    assert prim_table[p.NOTEQUAL](mock([2,2])) == fimg.w_false

def test_float_boolean():
    assert prim_table[p.FLOAT_LESSTHAN](mock([1.0,2.0])) == fimg.w_true
    assert prim_table[p.FLOAT_GREATERTHAN](mock([3.0,4.0])) == fimg.w_false
    assert prim_table[p.FLOAT_LESSOREQUAL](mock([1.3,2.6])) == fimg.w_true
    assert prim_table[p.FLOAT_GREATEROREQUAL](mock([3.5,4.9])) == fimg.w_false
    assert prim_table[p.FLOAT_EQUAL](mock([2.2,2.2])) == fimg.w_true
    assert prim_table[p.FLOAT_NOTEQUAL](mock([2.2,2.2])) == fimg.w_false
