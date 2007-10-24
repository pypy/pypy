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
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.w_class is w_mycls
    assert w_myinstance.fetch(0) is None
    py.test.raises(IndexError, lambda: w_myinstance.fetch(3))
    w_myinstance.store(1, w_myinstance)
    assert w_myinstance.fetch(1) is w_myinstance

def test_bytes_object():
    w_class = model.W_Class(None, None, format=model.BYTES)
    w_bytes = w_class.new(20)
    assert w_bytes.w_class is w_class
    assert w_bytes.size() == 20
    assert w_bytes.instvarsize() == 0
    assert w_bytes.getbyte(3) == 00
    w_bytes.setbyte(3, 0xAA)  
    assert w_bytes.getbyte(3) == 0xAA
    assert w_bytes.getbyte(0) == 0x00
    py.test.raises(IndexError, lambda: w_bytes.getbyte(20))

def test_word_object():
    w_class = model.W_Class(None, None, format=model.WORDS)
    w_bytes = w_class.new(20)
    assert w_bytes.w_class is w_class
    assert w_bytes.size() == 20
    assert w_bytes.instvarsize() == 0
    assert w_bytes.getword(3) == 0
    w_bytes.setword(3, 42)  
    assert w_bytes.getword(3) == 42
    assert w_bytes.getword(0) == 0
    py.test.raises(IndexError, lambda: w_bytes.getword(20))

def test_method_lookup():
	w_class = model.W_Class(None, None)
	w_class.methoddict["foo"] = 1
	w_class.methoddict["bar"] = 2
	w_subclass = model.W_Class(None, w_class)
	w_subclass.methoddict["foo"] = 3
	assert w_class.lookup("foo") == 1
	assert w_class.lookup("bar") == 2
	assert w_class.lookup("zork") == None
	assert w_subclass.lookup("foo") == 3
	assert w_subclass.lookup("bar") == 2
	assert w_subclass.lookup("zork") == None

def test_w_compiledin():
        w_super = model.W_Class(None,None)
        w_class = model.W_Class(None,w_super)
        w_super.installmethod("foo",
                              model.W_CompiledMethod(None, 0))
        assert w_class.lookup("foo").w_compiledin == w_super
