class AppTestFstring:
    def test_error_unknown_code(self):
        """
        def fn():
            f'{1000:j}'
        exc_info = raises(ValueError, fn)
        assert str(exc_info.value).startswith("Unknown format code")
        """
