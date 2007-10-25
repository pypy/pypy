from pypy.lang.smalltalk import classtable

def ismetaclass(w_cls):
    # Heuristic to detect if this is a metaclass. Don't use apart
    # from in this test file, because classtable['w_Metaclass'] is
    # bogus after loading an image.
    return w_cls.w_class is classtable.classtable['w_Metaclass']

def test_every_class_is_an_instance_of_a_metaclass():
    for (nm, w_cls) in classtable.classtable.items():
        assert ismetaclass(w_cls) or ismetaclass(w_cls.w_class)

def test_every_metaclass_inherits_from_class_and_behavior():
    s_Class = classtable.classtable['w_Class'].as_class_get_shadow()
    s_Behavior = classtable.classtable['w_Behavior'].as_class_get_shadow()
    for (nm, w_cls) in classtable.classtable.items():
        if ismetaclass(w_cls):
            shadow = w_cls.as_class_get_shadow()
            assert shadow.inherits_from(s_Class)
    assert s_Class.inherits_from(s_Behavior)

def test_metaclass_of_metaclass_is_an_instance_of_metaclass():
    w_Metaclass = classtable.classtable['w_Metaclass']
    assert w_Metaclass.w_class.w_class is w_Metaclass
