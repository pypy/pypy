from pypy.lang.scheme.object import *

def test_false():
	w_false = W_False()
	assert w_false.to_boolean() is False
	assert isinstance(w_false, W_Boolean)

def test_true():
	w_true = W_True()
	assert w_true.to_boolean() is True
	assert isinstance(w_true, W_Boolean)

