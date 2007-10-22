from pypy.lang.smalltalk import model

def test_new():
    w_mycls = model.W_Class(None, None)
    w_myinstance = w_mycls.new()
    assert isinstance(w_myinstance, model.W_Object)
    assert w_myinstance.w_class is w_mycls
