from pypy.lang.smalltalk import classtable

def ismetaclass(shadow):
    # Heuristic to detect if this is the shadow of a metaclass. Don't use
    # apart from in this test file, because classtable['w_Metaclass'] is
    # bogus after loading an image.
    return shadow.s_metaclass.w_self is classtable.classtable['w_Metaclass']

def test_every_class_is_an_instance_of_a_metaclass():
    for (nm, w_cls) in classtable.classtable.items():
        shadow = w_cls.as_class_get_shadow()
        assert ismetaclass(shadow) or ismetaclass(shadow.s_metaclass)

def test_every_metaclass_inherits_from_class_and_behavior():
    s_Class = classtable.classtable['w_Class'].as_class_get_shadow()
    s_Behavior = classtable.classtable['w_Behavior'].as_class_get_shadow()
    for (nm, w_cls) in classtable.classtable.items():
        shadow = w_cls.as_class_get_shadow()
        if ismetaclass(shadow):
            assert shadow.inherits_from(s_Class)
    assert s_Class.inherits_from(s_Behavior)

def test_metaclass_of_metaclass_is_an_instance_of_metaclass():
    s_Metaclass = classtable.classtable['w_Metaclass'].as_class_get_shadow()
    assert s_Metaclass.s_metaclass.s_metaclass is s_Metaclass

