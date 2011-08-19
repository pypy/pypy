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

    def test_parent(self):
        from greenlet import greenlet
        gmain = greenlet.getcurrent()
        assert gmain.parent is None
        g = greenlet(lambda: None)
        assert g.parent is gmain

    def test_pass_around(self):
        from greenlet import greenlet
        seen = []
        def f(x, y):
            seen.append((x, y))
            seen.append(greenlet.getcurrent().parent.switch())
            seen.append(greenlet.getcurrent().parent.switch(42))
            return 44, 'z'
        g = greenlet(f)
        seen.append(g.switch(40, 'x'))
        seen.append(g.switch(41, 'y'))
        seen.append(g.switch(43))
        #
        def f2():
            return 45
        g = greenlet(f2)
        seen.append(g.switch())
        #
        def f3():
            pass
        g = greenlet(f3)
        seen.append(g.switch())
        #
        assert seen == [(40, 'x'), (), (41, 'y'), 42, 43, (44, 'z'), 45, None]

    def test_exception_simple(self):
        from greenlet import greenlet
        #
        def fmain():
            raise ValueError
        #
        g1 = greenlet(fmain)
        raises(ValueError, g1.switch)

    def test_dead(self):
        from greenlet import greenlet
        #
        def fmain():
            assert g1 and not g1.dead
        #
        g1 = greenlet(fmain)
        assert not g1 and not g1.dead
        g1.switch()
        assert not g1 and g1.dead

    def test_GreenletExit(self):
        from greenlet import greenlet, GreenletExit
        #
        def fmain(*args):
            raise GreenletExit(*args)
        #
        g1 = greenlet(fmain)
        res = g1.switch('foo', 'bar')
        assert isinstance(res, GreenletExit) and res.args == ('foo', 'bar')
