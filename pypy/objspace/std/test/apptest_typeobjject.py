from pytest import raises


def test_nodoc():
    class NoDoc(object):
        pass

    try:
        assert NoDoc.__doc__ == None
    except AttributeError:
        raise AssertionError("__doc__ missing!")

def test_explicitdoc():
    class ExplicitDoc(object):
        __doc__ = 'foo'

    assert ExplicitDoc.__doc__ == 'foo'

def test_implicitdoc():
    class ImplicitDoc(object):
        "foo"

    assert ImplicitDoc.__doc__ == 'foo'

def test_set_doc():
    class X:
        "elephant"
    X.__doc__ = "banana"
    assert X.__doc__ == "banana"
    raises(TypeError, lambda:
           type(list).__dict__["__doc__"].__set__(list, "blah"))
    raises((AttributeError, TypeError), lambda:
           type(X).__dict__["__doc__"].__delete__(X))
    assert X.__doc__ == "banana"

def test_text_signature():
    assert object.__text_signature__ == '()'


    class BufferedReader(object):
        """BufferedReader(raw, buffer_size=DEFAULT_BUFFER_SIZE)\n--\n\n
        Create a new buffered reader using the given readable raw IO object.
        """
        pass


    assert BufferedReader.__doc__ == """BufferedReader(raw, buffer_size=DEFAULT_BUFFER_SIZE)\n--\n\n
        Create a new buffered reader using the given readable raw IO object.
        """
    assert BufferedReader.__text_signature__ == "(raw, buffer_size=DEFAULT_BUFFER_SIZE)"

def test_nodoc_text_signature():
    class NoDoc(object):
        pass

    assert NoDoc.__text_signature__ is None

def test_text_signature_on_function_type():
    def a(): pass
    result = getattr(type(a), '__text_signature__')
    assert result is None or isinstance(result, str)

def test_text_signature_on_builtin_function_type():
    result = getattr(type(len), '__text_signature__')
    assert result is None or isinstance(result, str)

def test_set_name():
    class Descriptor:
        def __set_name__(self, owner, name):
            self.owner = owner
            self.name = name

    class X:
        a = Descriptor()
    assert X.a.owner is X
    assert X.a.name == "a"

def test_set_name_error():
    class Descriptor:
        __set_name__ = None
    def make_class():
        class A:
            d = Descriptor()
    excinfo = raises(TypeError, make_class)
    assert excinfo.value.__notes__ == [
        "Error calling __set_name__ on 'Descriptor' instance 'd' in 'A'"]

def test_set_name_self():
    # issue 3326: modifying self.__dict__ in self.__set_name__
    class Descriptor:
        def __set_name__(self, owner, name):
            setattr(owner, "attr", self)

    class Foo:
        desc = Descriptor()
        desc2 = Descriptor()

    pass # does not crash
