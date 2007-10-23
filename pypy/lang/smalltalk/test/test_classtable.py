from pypy.lang.smalltalk.classtable import classtable
import pypy.lang.smalltalk.classtable as ct

def inherits_from(w_cls, w_superclass):
    w_p = w_cls
    while w_p and w_p != w_superclass:
        w_p = w_p.w_superclass
    return w_p == w_superclass

def test_every_class_is_an_instance_of_a_metaclass():
    for (nm, w_cls) in classtable.items():
        assert w_cls.ismetaclass() or w_cls.w_class.ismetaclass() # ?
        
def test_every_metaclass_inherits_from_class_and_behavior():
    for (nm, w_cls) in classtable.items():
        if w_cls.ismetaclass():
            assert inherits_from(w_cls, ct.w_Class)
    assert inherits_from(ct.w_Class, ct.w_Behavior)

def test_every_metaclass_is_an_instance_of_metaclass():
    for (nm, w_cls) in classtable.items():
        if w_cls.ismetaclass():
            assert w_cls.w_class is ct.w_Metaclass

def test_metaclass_of_metaclass_is_an_instance_of_metaclass():
    assert ct.w_Metaclass.w_class.w_class is ct.w_Metaclass
    
        


