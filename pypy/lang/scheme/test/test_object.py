import py
from pypy.lang.scheme.object import *
from pypy.lang.scheme.execution import ExecutionContext, Location

def test_false():
    w_false = W_Boolean(False)
    assert w_false.to_boolean() is False

def test_true():
    w_true = W_Boolean(True)
    assert w_true.to_boolean() is True

def test_string():
    str = "Hello World!"
    w_str = W_String(str)
    assert str == w_str.to_string()
    assert w_str.to_boolean() is True
    
def test_fixnum():
    num = 12345
    w_num = W_Integer(num)
    assert num == w_num.to_fixnum()
    assert float(num) == w_num.to_float()
    assert w_num.to_boolean() is True

def test_float():
    num = 12345.567
    w_num = W_Real(num)
    assert num == w_num.to_float()
    assert int(num) == w_num.to_fixnum()
    assert w_num.to_boolean() is True

def test_pair():
    c1 = W_Integer(1)
    c2 = W_String("c2")
    c3 = W_Real(0.3)
    c4 = W_Nil()
    p2 = W_Pair(c3, c4)
    p1 = W_Pair(c2, p2)
    p = W_Pair(c1, p1)
    assert p.car == c1
    assert p.cdr.car == c2
    assert p.cdr.cdr.car == c3
    assert p.cdr.cdr.cdr == c4
    assert p.to_boolean() is True
    assert c4.to_boolean() is True

def test_symbol():
    w_sym = W_Symbol("symb")
    assert w_sym.to_string() == "symb"
    assert w_sym.to_boolean() is True

def test_symbol():
    w_id = W_Symbol("ident")
    assert w_id.to_string() == "ident"
    assert w_id.to_boolean() is True

def test_ctx():
    w_fnum = W_Integer(12)
    w_symb = W_Symbol("symb")

    ctx = ExecutionContext()
    ctx.put("v1", w_fnum)
    ctx.put("symb", w_symb)

    assert w_symb is ctx.get("symb")
    assert w_fnum is ctx.get("v1")
    py.test.raises(UnboundVariable, ctx.get, "no_such_key")

def test_location():
    w_fnum = W_Integer(42)
    loc = Location(w_fnum)
    assert isinstance(loc, Location)
    assert loc.obj is w_fnum

def test_ctx_sets():
    w_fnum = W_Integer(42)
    w_fnum2 = W_Integer(43)
    w_fnum3 = W_Integer(44)

    ctx = ExecutionContext()
    ctx.put("v1", w_fnum)

    ctx2 = ctx.copy()
    assert w_fnum is ctx2.get("v1")
    ctx.set("v1", w_fnum2)
    assert w_fnum2 is ctx2.get("v1")
    assert w_fnum2 is ctx.get("v1")

    ctx2.put("v1", w_fnum3)
    assert w_fnum3 is ctx2.get("v1")

