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
