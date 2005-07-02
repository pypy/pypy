

class AppTestSyntaxErr:

    def test_synerr(self):
        def x():
            exec "1 2"
        raises(SyntaxError, x)
