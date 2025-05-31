import pytest

def test_property_name_in_error():
    class A:
        @property
        def my_funny_attribute(self):
            return 1

        unreadable = property()
        @unreadable.setter
        def even_funnier(self, value):
            pass

    with pytest.raises(AttributeError) as info:
        A().my_funny_attribute = 1
    assert "my_funny_attribute" in str(info.value)

    with pytest.raises(AttributeError) as info:
        del A().my_funny_attribute
    assert "my_funny_attribute" in str(info.value)

    with pytest.raises(AttributeError) as info:
        A().even_funnier
    assert "even_funnier" in str(info.value)

def test_property_name_in_error_setter():
    class A:
        pass
    p = property(lambda self: 1)
    p.__set_name__(A, "it_propagates")
    p = p.setter(lambda self, value: None)
    with pytest.raises(AttributeError) as info:
        p.__delete__(A())
    assert "it_propagates" in str(info.value)

def test_property_class_qualname_in_error():
    class ThisNiceNewFeature:
        @property
        def my_funny_attribute(self):
            return 1

        unreadable = property()
        @unreadable.setter
        def even_funnier(self, value):
            pass

    with pytest.raises(AttributeError) as info:
        ThisNiceNewFeature().my_funny_attribute = 1
    assert str(info.value) == "property 'my_funny_attribute' of 'test_property_class_qualname_in_error.<locals>.ThisNiceNewFeature' object has no setter"

    with pytest.raises(AttributeError) as info:
        del ThisNiceNewFeature().my_funny_attribute
    assert "ThisNiceNewFeature" in str(info.value)

    with pytest.raises(AttributeError) as info:
        ThisNiceNewFeature().unreadable
    assert "ThisNiceNewFeature" in str(info.value)


def test_dont_segfault():

    class pro(property):
        def __new__(typ, *args, **kwargs):
            return "abcdef"
    class A:
        pass

    p = property.__new__(pro)
    p.__set_name__(A, 1)
    p.getter(lambda self: 1) # must not crash

def test_super_error_message():
    with raises(TypeError) as info:
        super(1, int)
    assert str(info.value) == "super() argument 1 must be a type, not int"
