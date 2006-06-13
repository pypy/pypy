from pypy.conftest import gettestobjspace

class AppTest_Stackless:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('stackless',))
        cls.space = space

    def test_one(self):
        import stackless
        print stackless.__file__
        t = stackless.tasklet()
        t.demo()
        class A(stackless.tasklet):
            def __init__(self, name):
                self.name = name
            def __new__(subtype, *args):
                return stackless.tasklet.__new__(subtype)
        x = A("heinz")
        x.demo()
        print x.name
