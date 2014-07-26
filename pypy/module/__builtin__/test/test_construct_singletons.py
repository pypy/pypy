class AppTestConstructSingletons:

    def test_construct_singletons(self):
        none_type = type(None)
        assert none_type() is None
        raises(TypeError, none_type, 1, 2)
        raises(TypeError, none_type, a=1, b=2)
