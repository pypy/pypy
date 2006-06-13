from pypy.conftest import gettestobjspace

class AppTest_Stackless:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def x_test_one(self):
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

    def test_simple(self):
        import stackless

        rlist = []

        def f():
            rlist.append('f')

        def g():
            rlist.append('g')
            stackless.schedule()

        def main():
            rlist.append('m')
            cg = stackless.tasklet(g)()
            cf = stackless.tasklet(f)()
            stackless.run()
            rlist.append('m')

        main()

        assert stackless.getcurrent() is stackless.main_tasklet
        assert rlist == 'm g f m'.split()

