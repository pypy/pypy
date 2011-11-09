from pypy.conftest import gettestobjspace


class AppTestGreenlet:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_continuation'], continuation=True)

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
        #
        gmain = greenlet.getcurrent()
        assert gmain and not gmain.dead

    def test_GreenletExit(self):
        from greenlet import greenlet, GreenletExit
        #
        def fmain(*args):
            raise GreenletExit(*args)
        #
        g1 = greenlet(fmain)
        res = g1.switch('foo', 'bar')
        assert isinstance(res, GreenletExit) and res.args == ('foo', 'bar')

    def test_throw_1(self):
        from greenlet import greenlet
        gmain = greenlet.getcurrent()
        #
        def f():
            try:
                gmain.switch()
            except ValueError:
                return "ok"
        #
        g = greenlet(f)
        g.switch()
        res = g.throw(ValueError)
        assert res == "ok"

    def test_throw_2(self):
        from greenlet import greenlet
        gmain = greenlet.getcurrent()
        #
        def f():
            gmain.throw(ValueError)
        #
        g = greenlet(f)
        raises(ValueError, g.switch)

    def test_throw_3(self):
        from greenlet import greenlet
        gmain = greenlet.getcurrent()
        raises(ValueError, gmain.throw, ValueError)

    def test_throw_4(self):
        from greenlet import greenlet
        gmain = greenlet.getcurrent()
        #
        def f1():
            g2.throw(ValueError)
        #
        def f2():
            try:
                gmain.switch()
            except ValueError:
                return "ok"
        #
        g1 = greenlet(f1)
        g2 = greenlet(f2)
        g2.switch()
        res = g1.switch()
        assert res == "ok"

    def test_nondefault_parent(self):
        from greenlet import greenlet
        #
        def f1():
            g2 = greenlet(f2)
            res = g2.switch()
            assert res == "from 2"
            return "from 1"
        #
        def f2():
            return "from 2"
        #
        g1 = greenlet(f1)
        res = g1.switch()
        assert res == "from 1"

    def test_change_parent(self):
        from greenlet import greenlet
        #
        def f1():
            res = g2.switch()
            assert res == "from 2"
            return "from 1"
        #
        def f2():
            return "from 2"
        #
        g1 = greenlet(f1)
        g2 = greenlet(f2)
        g2.parent = g1
        res = g1.switch()
        assert res == "from 1"

    def test_raises_through_parent_chain(self):
        from greenlet import greenlet
        #
        def f1():
            raises(IndexError, g2.switch)
            raise ValueError
        #
        def f2():
            raise IndexError
        #
        g1 = greenlet(f1)
        g2 = greenlet(f2)
        g2.parent = g1
        raises(ValueError, g1.switch)

    def test_switch_to_dead_1(self):
        from greenlet import greenlet
        #
        def f1():
            return "ok"
        #
        g1 = greenlet(f1)
        res = g1.switch()
        assert res == "ok"
        res = g1.switch("goes to gmain instead")
        assert res == "goes to gmain instead"

    def test_switch_to_dead_2(self):
        from greenlet import greenlet
        #
        def f1():
            g2 = greenlet(f2)
            return g2.switch()
        #
        def f2():
            return "ok"
        #
        g1 = greenlet(f1)
        res = g1.switch()
        assert res == "ok"
        res = g1.switch("goes to gmain instead")
        assert res == "goes to gmain instead"

    def test_switch_to_dead_3(self):
        from greenlet import greenlet
        gmain = greenlet.getcurrent()
        #
        def f1():
            res = g2.switch()
            assert res == "ok"
            res = gmain.switch("next step")
            assert res == "goes to f1 instead"
            return "all ok"
        #
        def f2():
            return "ok"
        #
        g1 = greenlet(f1)
        g2 = greenlet(f2)
        g2.parent = g1
        res = g1.switch()
        assert res == "next step"
        res = g2.switch("goes to f1 instead")
        assert res == "all ok"

    def test_throw_in_not_started_yet(self):
        from greenlet import greenlet
        #
        def f1():
            never_reached
        #
        g1 = greenlet(f1)
        raises(ValueError, g1.throw, ValueError)
        assert g1.dead

    def test_exc_info_save_restore(self):
        # sys.exc_info save/restore behaviour is wrong on CPython's greenlet
        from greenlet import greenlet
        import sys
        def f():
            try:
                raise ValueError('fun')
            except:
                exc_info = sys.exc_info()
                greenlet(h).switch()
                assert exc_info == sys.exc_info()

        def h():
            assert sys.exc_info() == (None, None, None)

        greenlet(f).switch()

    def test_gr_frame(self):
        from greenlet import greenlet
        import sys
        def f2():
            assert g.gr_frame is None
            gmain.switch()
            assert g.gr_frame is None
        def f1():
            assert gmain.gr_frame is gmain_frame
            assert g.gr_frame is None
            f2()
            assert g.gr_frame is None
        gmain = greenlet.getcurrent()
        assert gmain.gr_frame is None
        gmain_frame = sys._getframe()
        g = greenlet(f1)
        assert g.gr_frame is None
        g.switch()
        assert g.gr_frame.f_code.co_name == 'f2'
        g.switch()
        assert g.gr_frame is None
