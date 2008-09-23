import py
from pypy.lang.smalltalk import model, shadow
from pypy.lang.smalltalk.shadow import MethodNotFound
from pypy.lang.smalltalk import objspace

mockclass = objspace.bootstrap_class

space = objspace.ObjSpace()

def joinbits(values, lengths):
    result = 0
    for each, length in reversed(zip(values, lengths)):
        result = result << length
        result += each
    return result   


def test_new():
    w_mycls = mockclass(space, 0)
    w_myinstance = w_mycls.as_class_get_shadow(space).new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclass(space).is_same_object(w_mycls)
    assert w_myinstance.shadow_of_my_class(space) is w_mycls.as_class_get_shadow(space)

def test_new_namedvars():
    w_mycls = mockclass(space, 3)
    w_myinstance = w_mycls.as_class_get_shadow(space).new()
    assert isinstance(w_myinstance, model.W_PointersObject)
    assert w_myinstance.getclass(space).is_same_object(w_mycls)
    assert w_myinstance.fetch(space, 0) is space.w_nil
    py.test.raises(IndexError, lambda: w_myinstance.fetch(space, 3))
    w_myinstance.store(space, 1, w_myinstance)
    assert w_myinstance.fetch(space, 1) is w_myinstance

def test_bytes_object():
    w_class = mockclass(space, 0, format=shadow.BYTES)
    w_bytes = w_class.as_class_get_shadow(space).new(20)
    assert w_bytes.getclass(space).is_same_object(w_class)
    assert w_bytes.size() == 20
    assert w_class.as_class_get_shadow(space).instsize() == 0
    assert w_bytes.getchar(3) == "\x00"
    w_bytes.setchar(3, "\xAA")
    assert w_bytes.getchar(3) == "\xAA"
    assert w_bytes.getchar(0) == "\x00"
    py.test.raises(IndexError, lambda: w_bytes.getchar(20))

def test_word_object():
    w_class = mockclass(space, 0, format=shadow.WORDS)
    w_bytes = w_class.as_class_get_shadow(space).new(20)
    assert w_bytes.getclass(space).is_same_object(w_class)
    assert w_bytes.size() == 20
    assert w_class.as_class_get_shadow(space).instsize() == 0
    assert w_bytes.getword(3) == 0
    w_bytes.setword(3, 42)  
    assert w_bytes.getword(3) == 42
    assert w_bytes.getword(0) == 0
    py.test.raises(IndexError, lambda: w_bytes.getword(20))

def test_method_lookup():
    w_class = mockclass(space, 0)
    shadow = w_class.as_class_get_shadow(space)
    shadow.installmethod("foo", 1)
    shadow.installmethod("bar", 2)
    w_subclass = mockclass(space, 0, w_superclass=w_class)
    subshadow = w_subclass.as_class_get_shadow(space)
    assert subshadow.s_superclass() is shadow
    subshadow.installmethod("foo", 3)
    shadow.initialize_methoddict()
    subshadow.initialize_methoddict()
    assert shadow.lookup("foo") == 1
    assert shadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, shadow.lookup, "zork")
    assert subshadow.lookup("foo") == 3
    assert subshadow.lookup("bar") == 2
    py.test.raises(MethodNotFound, subshadow.lookup, "zork")

def test_w_compiledin():
    w_super = mockclass(space, 0)
    w_class = mockclass(space, 0, w_superclass=w_super)
    supershadow = w_super.as_class_get_shadow(space)
    supershadow.installmethod("foo", model.W_CompiledMethod(0))
    classshadow = w_class.as_class_get_shadow(space)
    classshadow.initialize_methoddict()
    assert classshadow.lookup("foo").w_compiledin is w_super

def test_compiledmethod_setchar():
    w_method = model.W_CompiledMethod(3)
    w_method.setchar(0, "c")
    assert w_method.bytes == "c\x00\x00"

def test_hashes():
    w_five = model.W_SmallInteger(5)
    assert w_five.gethash() == 5
    w_class = mockclass(space, 0)
    w_inst = w_class.as_class_get_shadow(space).new()
    assert w_inst.hash == w_inst.UNASSIGNED_HASH
    h1 = w_inst.gethash()
    h2 = w_inst.gethash()
    assert h1 == h2
    assert h1 == w_inst.hash

def test_compiledmethod_at0():
    w_method = model.W_CompiledMethod()
    w_method.bytes = "abc"
    w_method.header = 100
    w_method.literals = [ 'lit1', 'lit2' ]
    w_method.literalsize = 2
    assert space.unwrap_int(w_method.at0(space, 0)) == 100
    assert w_method.at0(space, 4) == 'lit1'
    assert w_method.at0(space, 8) == 'lit2'
    assert space.unwrap_int(w_method.at0(space, 12)) == ord('a')
    assert space.unwrap_int(w_method.at0(space, 13)) == ord('b')
    assert space.unwrap_int(w_method.at0(space, 14)) == ord('c')

def test_compiledmethod_atput0():
    w_method = model.W_CompiledMethod(3)
    newheader = joinbits([0,2,0,0,0,0],[9,8,1,6,4,1])
    assert w_method.getliteralsize() == 0
    w_method.atput0(space, 0, space.wrap_int(newheader))
    assert w_method.getliteralsize() == 8 # 2 from new header * BYTES_PER_WORD (= 4)
    w_method.atput0(space, 4, 'lit1')
    w_method.atput0(space, 8, 'lit2')
    w_method.atput0(space, 12, space.wrap_int(ord('a')))
    w_method.atput0(space, 13, space.wrap_int(ord('b')))
    w_method.atput0(space, 14, space.wrap_int(ord('c')))
    assert space.unwrap_int(w_method.at0(space, 0)) == newheader
    assert w_method.at0(space, 4) == 'lit1'
    assert w_method.at0(space, 8) == 'lit2'
    assert space.unwrap_int(w_method.at0(space, 12)) == ord('a')
    assert space.unwrap_int(w_method.at0(space, 13)) == ord('b')
    assert space.unwrap_int(w_method.at0(space, 14)) == ord('c')

def test_is_same_object(w_o1=model.W_PointersObject(None,0), w_o2=None):
    if w_o2 is None:
        w_o2 = w_o1
    assert w_o1.is_same_object(w_o2)
    assert w_o2.is_same_object(w_o1)
    
def test_not_is_same_object(w_o1=model.W_PointersObject(None,0),w_o2=model.W_PointersObject(None,0)):
    assert not w_o1.is_same_object(w_o2)
    assert not w_o2.is_same_object(w_o1)
    w_o2 = model.W_SmallInteger(2)
    assert not w_o1.is_same_object(w_o2)
    assert not w_o2.is_same_object(w_o1)
    w_o2 = model.W_Float(5.5)
    assert not w_o1.is_same_object(w_o2)
    assert not w_o2.is_same_object(w_o1)

def test_intfloat_is_same_object():
    test_is_same_object(model.W_SmallInteger(1), model.W_SmallInteger(1))
    test_is_same_object(model.W_SmallInteger(100), model.W_SmallInteger(100))
    test_is_same_object(model.W_Float(1.100), model.W_Float(1.100))

def test_intfloat_notis_same_object():
    test_not_is_same_object(model.W_SmallInteger(1), model.W_Float(1))
    test_not_is_same_object(model.W_Float(100), model.W_SmallInteger(100))
    test_not_is_same_object(model.W_Float(1.100), model.W_Float(1.200))
    test_not_is_same_object(model.W_SmallInteger(101), model.W_SmallInteger(100))

def test_charis_same_object():
    test_is_same_object(space.wrap_char('a'), space.wrap_char('a'))
    test_is_same_object(space.wrap_char('d'), space.wrap_char('d'))

def test_not_charis_same_object():
    test_not_is_same_object(space.wrap_char('a'), space.wrap_char('d'))
    test_not_is_same_object(space.wrap_char('d'), space.wrap_int(3))
    test_not_is_same_object(space.wrap_char('d'), space.wrap_float(3.0))

def test_become_pointers():
    w_clsa = mockclass(space, 3)
    w_a = w_clsa.as_class_get_shadow(space).new()

    w_clsb = mockclass(space, 4)
    w_b = w_clsb.as_class_get_shadow(space).new()
    
    hasha = w_a.gethash()
    hashb = w_b.gethash()

    w_a.store(space, 0, w_b)
    w_b.store(space, 1, w_a)
    
    res = w_a.become(w_b)
    assert res
    assert w_a.gethash() == hashb
    assert w_b.gethash() == hasha

    assert w_a.getclass(space).is_same_object(w_clsb)
    assert w_b.getclass(space).is_same_object(w_clsa)

    assert w_b.fetch(space, 0) is w_b
    assert w_a.fetch(space, 1) is w_a

def test_become_with_shadow():
    w_clsa = mockclass(space, 3)
    s_clsa = w_clsa.as_class_get_shadow(space)
    w_clsb = mockclass(space, 4)
    s_clsb = w_clsb.as_class_get_shadow(space)
    res = w_clsa.become(w_clsb)
    assert res
    assert w_clsa.as_class_get_shadow(space) is s_clsb
    assert w_clsb.as_class_get_shadow(space) is s_clsa

def test_word_atput():
    i = model.W_SmallInteger(100)
    b = model.W_WordsObject(None, 1)
    b.atput0(space, 0, i)
    assert 100 == b.getword(0)
    i = space.classtable['w_LargePositiveInteger'].as_class_get_shadow(space).new(4)
    i.atput0(space, 3, space.wrap_int(192))
    b.atput0(space, 0, i)
    assert b.getword(0) == 3221225472

def test_word_at():
    b = model.W_WordsObject(None, 1)
    b.setword(0, 100)
    r = b.at0(space, 0)
    assert isinstance(r, model.W_SmallInteger)
    assert space.unwrap_int(r) == 100

    b.setword(0, 3221225472)
    r = b.at0(space, 0)
    assert isinstance(r, model.W_BytesObject)
    assert r.size() == 4
