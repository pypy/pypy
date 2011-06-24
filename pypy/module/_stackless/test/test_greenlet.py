from pypy.conftest import gettestobjspace, skip_on_missing_buildoption

class AppTest_Greenlet:

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


    def test_exc_info_save_restore(self):
        from _stackless import greenlet
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


# ____________________________________________________________
#
# The tests from greenlets.
# For now, without the ones that involve threads
#
class AppTest_PyMagicTestGreenlet:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space
        cls.w_glob = space.appexec([], """():
            import sys
            from _stackless import greenlet

            class SomeError(Exception):
                pass

            def fmain(seen):
                try:
                    greenlet.getcurrent().parent.switch()
                except:
                    seen.append(sys.exc_info()[0])
                    raise
                raise SomeError

            class Glob: pass
            glob = Glob()
            glob.__dict__.update(locals())
            return glob
        """)

    def test_simple(self):
        greenlet = self.glob.greenlet
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

    def test_exception(self):
        greenlet  = self.glob.greenlet
        fmain     = self.glob.fmain
        SomeError = self.glob.SomeError
        seen = []
        g1 = greenlet(fmain)
        g2 = greenlet(fmain)
        g1.switch(seen)
        g2.switch(seen)
        g2.parent = g1
        assert seen == []
        raises(SomeError, g2.switch)
        assert seen == [SomeError]
        g2.switch()
        assert seen == [SomeError]

    def test_send_exception(self):
        greenlet  = self.glob.greenlet
        fmain     = self.glob.fmain
        def send_exception(g, exc):
            # note: send_exception(g, exc)  can be now done with  g.throw(exc).
            # the purpose of this test is to explicitely check the
            # propagation rules.
            def crasher(exc):
                raise exc
            g1 = greenlet(crasher, parent=g)
            g1.switch(exc)

        seen = []
        g1 = greenlet(fmain)
        g1.switch(seen)
        raises(KeyError, "send_exception(g1, KeyError)")
        assert seen == [KeyError]

    def test_dealloc(self):
        skip("XXX in-progress: GC handling of greenlets")
        import gc
        greenlet = self.glob.greenlet
        fmain    = self.glob.fmain
        seen = []
        g1 = greenlet(fmain)
        g2 = greenlet(fmain)
        g1.switch(seen)
        g2.switch(seen)
        assert seen == []
        del g1
        gc.collect()
        assert seen == [greenlet.GreenletExit]
        del g2
        gc.collect()
        assert seen == [greenlet.GreenletExit, greenlet.GreenletExit]

    def test_frame(self):
        import sys
        greenlet = self.glob.greenlet
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


class AppTest_PyMagicTestThrow:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def test_class(self):
        from _stackless import greenlet
        def switch(*args):
            return greenlet.getcurrent().parent.switch(*args)

        def f():
            try:
                switch("ok")
            except RuntimeError:
                switch("ok")
                return
            switch("fail")

        g = greenlet(f)
        res = g.switch()
        assert res == "ok"
        res = g.throw(RuntimeError)
        assert res == "ok"

    def test_val(self):
        from _stackless import greenlet
        def switch(*args):
            return greenlet.getcurrent().parent.switch(*args)

        def f():
            try:
                switch("ok")
            except RuntimeError, val:
                if str(val) == "ciao":
                    switch("ok")
                    return
            switch("fail")

        g = greenlet(f)
        res = g.switch()
        assert res == "ok"
        res = g.throw(RuntimeError("ciao"))
        assert res == "ok"

        g = greenlet(f)
        res = g.switch()
        assert res == "ok"
        res = g.throw(RuntimeError, "ciao")
        assert res == "ok"

    def test_kill(self):
        from _stackless import greenlet
        def switch(*args):
            return greenlet.getcurrent().parent.switch(*args)

        def f():
            switch("ok")
            switch("fail")

        g = greenlet(f)
        res = g.switch()
        assert res == "ok"
        res = g.throw()
        assert isinstance(res, greenlet.GreenletExit)
        assert g.dead
        res = g.throw()    # immediately eaten by the already-dead greenlet
        assert isinstance(res, greenlet.GreenletExit)

    def test_throw_goes_to_original_parent(self):
        from _stackless import greenlet
        main = greenlet.getcurrent()
        def f1():
            try:
                main.switch("f1 ready to catch")
            except IndexError:
                return "caught"
            else:
                return "normal exit"
        def f2():
            main.switch("from f2")

        g1 = greenlet(f1)
        g2 = greenlet(f2, parent=g1)
        raises(IndexError, g2.throw, IndexError)
        assert g2.dead
        assert g1.dead

        g1 = greenlet(f1)
        g2 = greenlet(f2, parent=g1)
        res = g1.switch()
        assert res == "f1 ready to catch"
        res = g2.throw(IndexError)
        assert res == "caught"
        assert g2.dead
        assert g1.dead

        g1 = greenlet(f1)
        g2 = greenlet(f2, parent=g1)
        res = g1.switch()
        assert res == "f1 ready to catch"
        res = g2.switch()
        assert res == "from f2"
        res = g2.throw(IndexError)
        assert res == "caught"
        assert g2.dead
        assert g1.dead
            

class AppTest_PyMagicTestGenerator:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def test_generator(self):
        from _stackless import greenlet

        class genlet(greenlet):

            def __init__(self, *args, **kwds):
                self.args = args
                self.kwds = kwds

            def run(self):
                fn, = self.fn
                fn(*self.args, **self.kwds)

            def __iter__(self):
                return self

            def next(self):
                self.parent = greenlet.getcurrent()
                result = self.switch()
                if self:
                    return result
                else:
                    raise StopIteration

        def Yield(value):
            g = greenlet.getcurrent()
            while not isinstance(g, genlet):
                if g is None:
                    raise RuntimeError, 'yield outside a genlet'
                g = g.parent
            g.parent.switch(value)

        def generator(func):
            class generator(genlet):
                fn = (func,)
            return generator

        # ___ test starts here ___
        seen = []
        def g(n):
            for i in range(n):
                seen.append(i)
                Yield(i)
        g = generator(g)
        for k in range(3):
            for j in g(5):
                seen.append(j)
        assert seen == 3 * [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]


class AppTest_PyMagicTestGeneratorNested:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space
        cls.w_glob = space.appexec([], """():
            from _stackless import greenlet

            class genlet(greenlet):

                def __init__(self, *args, **kwds):
                    self.args = args
                    self.kwds = kwds
                    self.child = None

                def run(self):
                    fn, = self.fn
                    fn(*self.args, **self.kwds)

                def __iter__(self):
                    return self

                def set_child(self, child):
                    self.child = child

                def next(self):
                    if self.child:
                        child = self.child
                        while child.child:
                            tmp = child
                            child = child.child
                            tmp.child = None

                        result = child.switch()
                    else:
                        self.parent = greenlet.getcurrent()            
                        result = self.switch()

                    if self:
                        return result
                    else:
                        raise StopIteration

            def Yield(value, level = 1):
                g = greenlet.getcurrent()

                while level != 0:
                    if not isinstance(g, genlet):
                        raise RuntimeError, 'yield outside a genlet'
                    if level > 1:
                        g.parent.set_child(g)
                    g = g.parent
                    level -= 1

                g.switch(value)

            def Genlet(func):
                class Genlet(genlet):
                    fn = (func,)
                return Genlet

            class Glob: pass
            glob = Glob()
            glob.__dict__.update(locals())
            return glob
        """)

    def test_genlet_1(self):
        Genlet = self.glob.Genlet
        Yield  = self.glob.Yield

        def g1(n, seen):
            for i in range(n):
                seen.append(i+1)
                yield i

        def g2(n, seen):
            for i in range(n):
                seen.append(i+1)
                Yield(i)

        g2 = Genlet(g2)

        def nested(i):
            Yield(i)

        def g3(n, seen):
            for i in range(n):
                seen.append(i+1)
                nested(i)
        g3 = Genlet(g3)

        raises(RuntimeError, Yield, 10)
        for g in [g1, g2, g3]:
            seen = []
            for k in range(3):
                for j in g(5, seen):
                    seen.append(j)
            assert seen == 3 * [1, 0, 2, 1, 3, 2, 4, 3, 5, 4]
        raises(RuntimeError, Yield, 10)

    def test_nested_genlets(self):
        Genlet = self.glob.Genlet
        Yield  = self.glob.Yield
        def a(n):
            if n == 0:
                return
            for ii in ax(n-1):
                Yield(ii)
            Yield(n)
        ax = Genlet(a)
        seen = []
        for ii in ax(5):
            seen.append(ii)
        assert seen == [1, 2, 3, 4, 5]

    def test_perms(self):
        Genlet = self.glob.Genlet
        Yield  = self.glob.Yield
        def perms(l):
            if len(l) > 1:
                for e in l:
                    # No syntactical sugar for generator expressions
                    [Yield([e] + p) for p in perms([x for x in l if x!=e])]
            else:
                Yield(l)
        perms = Genlet(perms)
        gen_perms = perms(range(4))
        permutations = list(gen_perms)
        assert len(permutations) == 4*3*2*1
        assert [0,1,2,3] in permutations
        assert [3,2,1,0] in permutations

    def test_layered_genlets(self):
        Genlet = self.glob.Genlet
        Yield  = self.glob.Yield
        def gr1(n):
            for ii in range(1, n):
                Yield(ii)
                Yield(ii * ii, 2)
        gr1 = Genlet(gr1)
        def gr2(n, seen):
            for ii in gr1(n):
                seen.append(ii)
        gr2 = Genlet(gr2)
        seen = []
        for ii in gr2(5, seen):
            seen.append(ii)
        assert seen == [1, 1, 2, 4, 3, 9, 4, 16]
