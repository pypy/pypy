
class AppTest_IdHack:

    objspacename = 'idhack'

    def test_simple(self):
        x = 5
        y = 6
        assert x is not y
        become(x, y)
        assert x is y

    def test_id(self):
        # these are the Smalltalk semantics of become().
        x = 5; idx = id(x)
        y = 6; idy = id(y)
        assert idx != idy
        become(x, y)
        assert id(x) == id(y) == idy
