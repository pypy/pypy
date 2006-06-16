from pypy.conftest import gettestobjspace, skip_on_missing_buildoption

def setup_module(mod):
    skip_on_missing_buildoption(stackless=True)

class AppTest_Coroutine:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def test_very_simple(self):
        from _stackless import greenlet
        lst = []
        def f(x):
            lst.append(x)
            return x + 10
        g = greenlet(f)
        assert not g
        res = g.switch(20)
        assert res == 30
        assert lst == [20]
        assert g.dead
        assert not g

    def test_switch_back_to_main(self):
        from _stackless import greenlet
        lst = []
        main = greenlet.getcurrent()
        def f(x):
            lst.append(x)
            x = main.switch(x + 10)
            return 40 + x 
        g = greenlet(f)
        res = g.switch(20)
        assert res == 30
        assert lst == [20]
        assert not g.dead
        res = g.switch(2)
        assert res == 42
        assert g.dead

    def test_simple(self):
        from _stackless import greenlet
        lst = []
        gs = []
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

    def test_exception_simple(self):
        from _stackless import greenlet
        def f():
            raise ValueError
        g1 = greenlet(f)
        raises(ValueError, g1.switch)

    def test_exception_propagate(self):
        from _stackless import greenlet
        def f():
            raise ValueError
        def g():
            return g1.switch()
        g1 = greenlet(f)
        g2 = greenlet(g)
        raises(ValueError, g1.switch)
        g1 = greenlet(f)
        raises(ValueError, g2.switch)

    def test_exception(self):
        from _stackless import greenlet
        import sys
        def fmain(seen):
            try:
                greenlet.getcurrent().parent.switch()
            except:
                seen.append(sys.exc_info()[0])
                raise
            raise ValueError
        seen = []
        g1 = greenlet(fmain)
        g2 = greenlet(fmain)
        g1.switch(seen)
        g2.switch(seen)
        raises(TypeError, "g2.parent = 1")
        g2.parent = g1
        assert seen == []
        raises(ValueError, g2.switch)
        assert seen == [ValueError]
        g2.switch()
        assert seen == [ValueError]

    def test_send_exception(self):
        from _stackless import greenlet
        import sys
        def send_exception(g, exc):
            # note: send_exception(g, exc)  can be now done with  g.throw(exc).
            # the purpose of this test is to explicitely check the propagation rules.
            def crasher(exc):
                raise exc
            g1 = greenlet(crasher)
            g1.parent = g
            g1.switch(exc)
        def fmain(seen):
            try:
                greenlet.getcurrent().parent.switch()
            except:
                seen.append(sys.exc_info()[0])
                raise
            raise ValueError

        seen = []
        g1 = greenlet(fmain)
        g1.switch(seen)
        raises(KeyError, "send_exception(g1, KeyError)")
        assert seen == [KeyError]
        seen = []
        g1 = greenlet(fmain)
        g1.switch(seen)
        raises(KeyError, "g1.throw(KeyError)")
        assert seen == [KeyError]
        assert g1.dead

    def test_frame(self):
        from _stackless import greenlet
        import sys
        def f1():
            f = sys._getframe(0)
            assert f.f_back is None
            greenlet.getcurrent().parent.switch(f)
            return "meaning of life"
        g = greenlet(f1)
        frame = g.switch()
        assert frame is g.gr_frame
        assert g
        next = g.switch()
        assert not g
        assert next == "meaning of life"
        assert g.gr_frame is None

    def test_mixing_greenlet_coroutine(self):
        from _stackless import greenlet, coroutine
        lst = []
        def f():
            lst.append(1)
            greenlet.getcurrent().parent.switch()
            lst.append(3)
        def make_h(c):
            def h():
                g = greenlet(f)
                lst.append(0)
                g.switch()
                c.switch()
                lst.append(2)
                g.switch()
                c.switch()
                lst.append(4)
                c.switch()
            return h
        c1 = coroutine.getcurrent()
        c2 = coroutine()
        c3 = coroutine()
        c2.bind(make_h(c3))
        c3.bind(make_h(c2))
        c2.switch()
        assert lst == [0, 1, 0, 1, 2, 3, 2, 3, 4, 4]

    def test_dealloc(self):
        skip("not working yet")
        from _stackless import greenlet
        import sys
        def fmain(seen):
            try:
                greenlet.getcurrent().parent.switch()
            except:
                seen.append(sys.exc_info()[0])
                raise
            raise ValueError
        seen = []
        seen = []
        g1 = greenlet(fmain)
        g2 = greenlet(fmain)
        g1.switch(seen)
        g2.switch(seen)
        assert seen == []
        del g1
        assert seen == [greenlet.GreenletExit]
        del g2
        assert seen == [greenlet.GreenletExit, greenlet.GreenletExit]

