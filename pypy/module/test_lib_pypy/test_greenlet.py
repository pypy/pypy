from pypy.conftest import gettestobjspace


class AppTestGreenlet:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_continuation'])

    def test_simple(self):
        from greenlet import greenlet
        lst = []
        def f():
            lst.append(1)
            greenlet.getcurrent().parent.switch()
            lst.append(3)
        g = greenlet(f)
        lst.append(0)
        g.switch()
        lst.append(2)
        g.switch()
        lst.append(4)
        assert lst == range(5)
