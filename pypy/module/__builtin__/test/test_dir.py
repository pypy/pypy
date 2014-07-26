class AppTestDir:

    def test_dir_obj__dir__tuple(self):
        """When __dir__ method returns a tuple, python3 converts it to list."""

        class Foo(object):
            def __dir__(self):
                return ("b", "c", "a")

        res = dir(Foo())
        assert isinstance(res, list)
        assert res == ["a", "b", "c"]
