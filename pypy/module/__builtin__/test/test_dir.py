class AppTestDir:

    def test_dir_obj__dir__tuple(self):
        """If __dir__ method returns a tuple, cpython3 converts it to list."""
        class Foo(object):
            def __dir__(self):
                return ("b", "c", "a")
        res = dir(Foo())
        assert isinstance(res, list)
        assert res == ["a", "b", "c"]

    def test_dir_obj__dir__genexp(self):
        """Generator expression is also converted to list by cpython3."""
        class Foo(object):
            def __dir__(self):
                return (i for i in ["b", "c", "a"])
        res = dir(Foo())
        assert isinstance(res, list)
        assert res == ["a", "b", "c"]

    def test_dir_obj__dir__noniter(self):
        """If result of __dir__ is not iterable, it's an error."""
        class Foo(object):
            def __dir__(self):
                return 42
        raises(TypeError, dir, Foo())
