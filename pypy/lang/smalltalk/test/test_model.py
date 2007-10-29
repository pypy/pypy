import py
from pypy.lang.smalltalk import model, shadow, objtable
from pypy.lang.smalltalk.shadow import MethodNotFound
import pypy.lang.smalltalk.classtable as ct

mockclass = ct.bootstrap_class

def test_new():
    w_mycls = mockclass(0)
    w_myinstance = w_mycls.as_class_get_shadow().new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclass() is w_mycls
    assert w_myinstance.shadow_of_my_class() is w_mycls.as_class_get_shadow()

def test_new_namedvars():
    w_mycls = mockclass(3)
    w_myinstance = w_mycls.as_class_get_shadow().new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclass() is w_mycls
    assert w_myinstance.fetch(0) is objtable.w_nil
    py.test.raises(IndexError, lambda: w_myinstance.fetch(3))
    w_myinstance.store(1, w_myinstance)
    assert w_myinstance.fetch(1) is w_myinstance

def test_bytes_object():
    w_class = mockclass(0, format=shadow.BYTES)
    w_bytes = w_class.as_class_get_shadow().new(20)
    assert w_bytes.getclass() is w_class
    assert w_bytes.size() == 20
    assert w_class.as_class_get_shadow().instsize() == 0
    assert w_bytes.getbyte(3) == 00
    w_bytes.setbyte(3, 0xAA)  
    assert w_bytes.getbyte(3) == 0xAA
    assert w_bytes.getbyte(0) == 0x00
    py.test.raises(IndexError, lambda: w_bytes.getbyte(20))

def test_word_object():
    w_class = mockclass(0, format=shadow.WORDS)
    w_bytes = w_class.as_class_get_shadow().new(20)
    assert w_bytes.getclass() is w_class
    assert w_bytes.size() == 20
    assert w_class.as_class_get_shadow().instsize() == 0
    assert w_bytes.getword(3) == 0
    w_bytes.setword(3, 42)  
    assert w_bytes.getword(3) == 42
    assert w_bytes.getword(0) == 0
    py.test.raises(IndexError, lambda: w_bytes.getword(20))

def test_method_lookup():
    w_class = mockclass(0)
    shadow = w_class.as_class_get_shadow()
    shadow.methoddict["foo"] = 1
    shadow.methoddict["bar"] = 2
    w_subclass = mockclass(0, w_superclass=w_class)
    subshadow = w_subclass.as_class_get_shadow()
    assert subshadow.s_superclass is shadow
    subshadow.methoddict["foo"] = 3
    assert shadow.lookup("foo") == 1
    assert shadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, shadow.lookup, "zork")
    assert subshadow.lookup("foo") == 3
    assert subshadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, subshadow.lookup, "zork")

def test_w_compiledin():
    w_super = mockclass(0)
    w_class = mockclass(0, w_superclass=w_super)
    supershadow = w_super.as_class_get_shadow()
    supershadow.installmethod("foo", model.W_CompiledMethod(0, ""))
    classshadow = w_class.as_class_get_shadow()
    assert classshadow.lookup("foo").w_compiledin is w_super

def test_w_compiledin():
    w_method = model.W_CompiledMethod(0, "abc")
    w_method.setbyte(0, ord("c"))
    assert w_method.bytes == "cbc"

def test_hashes():
    w_five = model.W_SmallInteger(5)
    assert w_five.gethash() == 5
    w_class = mockclass(0)
    w_inst = w_class.as_class_get_shadow().new()
    assert w_inst.hash == w_inst.UNASSIGNED_HASH
    h1 = w_inst.gethash()
    h2 = w_inst.gethash()
    assert h1 == h2
    assert h1 == w_inst.hash
