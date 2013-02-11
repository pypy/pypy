
class AppTestPickle:

    def test_stack_underflow(self):
        import _pickle
        raises(TypeError, _pickle.loads, "a string")
