import py
from pypy.lang.smalltalk import model

def test_new():
    w_mycls = model.W_Class(None, None)
    w_myinstance = w_mycls.new()
    assert isinstance(w_myinstance, model.W_Object)
    assert w_myinstance.w_class is w_mycls

def test_new_namedvars():
    w_mycls = model.W_Class(None, None, 3)
    w_myinstance = w_mycls.new()
    assert isinstance(w_myinstance, model.W_NamedVarsObject)
    assert w_myinstance.w_class is w_mycls
    assert w_myinstance.getnamedvar(0) is None
    py.test.raises(IndexError, lambda: w_myinstance.getnamedvar(3))
    w_myinstance.setnamedvar(1, w_myinstance)
    assert w_myinstance.getnamedvar(1) is w_myinstance
