from pypy.lang.scheme.object import *

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
    
def test_fixnum():
    num = 12345
    w_num = W_Fixnum(num)
    assert num == w_num.to_fixnum()
    assert float(num) == w_num.to_float()

def test_float():
    num = 12345.567
    w_num = W_Float(num)
    assert num == w_num.to_float()
    assert int(num) == w_num.to_fixnum()

def test_pair():
    c1 = W_Fixnum(1)
    c2 = W_String("c2")
    c3 = W_Float(0.3)
    c4 = W_Nil()
    p2 = W_Pair(c3, c4)
    p1 = W_Pair(c2, p2)
    p = W_Pair(c1, p1)
    assert p.car == c1
    assert p.cdr.car == c2
    assert p.cdr.cdr.car == c3
    assert p.cdr.cdr.cdr == c4
