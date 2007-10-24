import py
from pypy.lang.smalltalk import model, mirror
import pypy.lang.smalltalk.classtable as ct

mockclassmirror = ct.bootstrap_classmirror

def test_new():
    m_mycls = mockclassmirror(0)
    w_myinstance = m_mycls.new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclassmirror() is m_mycls

def test_new_namedvars():
    m_mycls = mockclassmirror(3)
    w_myinstance = m_mycls.new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclassmirror() is m_mycls
    assert w_myinstance.fetch(0) is None
    py.test.raises(IndexError, lambda: w_myinstance.fetch(3))
    w_myinstance.store(1, w_myinstance)
    assert w_myinstance.fetch(1) is w_myinstance

def test_bytes_object():
    m_class = mockclassmirror(0, format=mirror.BYTES)
    w_bytes = m_class.new(20)
    assert w_bytes.getclassmirror() is m_class
    assert w_bytes.size() == 20
    assert m_class.instsize() == 0
    assert w_bytes.getbyte(3) == 00
    w_bytes.setbyte(3, 0xAA)  
    assert w_bytes.getbyte(3) == 0xAA
    assert w_bytes.getbyte(0) == 0x00
    py.test.raises(IndexError, lambda: w_bytes.getbyte(20))

def test_word_object():
    m_class = mockclassmirror(0, format=mirror.WORDS)
    w_bytes = m_class.new(20)
    assert w_bytes.getclassmirror() is m_class
    assert w_bytes.size() == 20
    assert m_class.instsize() == 0
    assert w_bytes.getword(3) == 0
    w_bytes.setword(3, 42)  
    assert w_bytes.getword(3) == 42
    assert w_bytes.getword(0) == 0
    py.test.raises(IndexError, lambda: w_bytes.getword(20))

def test_method_lookup():
    m_class = mockclassmirror(0)
    m_class.methoddict["foo"] = 1
    m_class.methoddict["bar"] = 2
    m_subclass = mockclassmirror(0, m_superclass=m_class)
    m_subclass.methoddict["foo"] = 3
    assert m_class.lookup("foo") == 1
    assert m_class.lookup("bar") == 2
    assert m_class.lookup("zork") == None
    assert m_subclass.lookup("foo") == 3
    assert m_subclass.lookup("bar") == 2
    assert m_subclass.lookup("zork") == None

def test_m_compiledin():
    m_super = mockclassmirror(0)
    m_class = mockclassmirror(0, m_superclass=m_super)
    m_super.installmethod("foo", model.W_CompiledMethod(0, ""))
    assert m_class.lookup("foo").m_compiledin is m_super
