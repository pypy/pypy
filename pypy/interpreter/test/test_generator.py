class AppTestGenerator:

    def test_generator(self):
        def f():
            yield 1
        assert f().next() == 1

    def test_generator2(self):
        def f():
            yield 1
        g = f()
        assert g.next() == 1
        raises(StopIteration, g.next)

    def test_attributes(self):
        def f():
            yield 1
            assert g.gi_running
        g = f()
        assert g.gi_code is f.func_code
        assert g.__name__ == 'f'
        assert g.gi_frame is not None
        assert not g.gi_running
        g.next()
        assert not g.gi_running
        raises(StopIteration, g.next)
        assert not g.gi_running
        assert g.gi_frame is None
        assert g.gi_code is f.func_code
        assert g.__name__ == 'f'

    def test_generator3(self):
        def f():
            yield 1
        g = f()
        assert list(g) == [1]

    def test_generator4(self):
        def f():
            yield 1
        g = f()
        assert [x for x in g] == [1]

    def test_generator5(self):
        d = {}
        exec """if 1:
        def f():
            v = (yield )
            yield v
        g = f()
        g.next()
        """ in d
        g = d['g']
        assert g.send(42) == 42

    def test_throw1(self):
        def f():
            yield 2
        g = f()
        raises(NameError, g.throw, NameError, "Error")

    def test_throw2(self):
        def f():
            yield 2
        g = f()
        raises(NameError, g.throw, NameError("Error"))

    def test_throw3(self):
        def f():
            try:
                yield 1
                yield 2
            except:
                yield 3
        g = f()
        assert g.next() == 1
        assert g.throw(NameError("Error")) == 3
        raises(StopIteration, g.next)

    def test_throw4(self):
        d = {}
        exec """if 1:
        def f():
            try:
                yield 1
                v = (yield 2)
            except:
                yield 3
        g = f()
        """ in d
        g = d['g']
        assert g.next() == 1
        assert g.next() == 2
        assert g.throw(NameError("Error")) == 3
        raises(StopIteration, g.next)

    def test_throw5(self):
        def f():
            try:
                yield 1
            except:
                x = 3
            try:
                yield x
            except:
                pass
        g = f()
        g.next()
        # String exceptions are not allowed anymore
        raises(TypeError, g.throw, "Error")
        assert g.throw(Exception) == 3
        raises(StopIteration, g.throw, Exception)

    def test_throw6(self):
        def f():
            yield 2
        g = f()
        raises(NameError, g.throw, NameError, "Error", None)


    def test_throw_fail(self):
        def f():
            yield 1
        g = f()
        raises(TypeError, g.throw, NameError("Error"), "error")

    def test_throw_fail2(self):
        def f():
            yield 1
        g = f()
        raises(TypeError, g.throw, list())

    def test_throw_fail3(self):
        def f():
            yield 1
        g = f()
        raises(TypeError, g.throw, NameError("Error"), None, "not tb object")

    def test_throw_finishes_generator(self):
        def f():
            yield 1
        g = f()
        assert g.gi_frame is not None
        raises(ValueError, g.throw, ValueError)
        assert g.gi_frame is None

    def test_throw_bug(self):
        def f():
            try:
                x.throw(IndexError)     # => "generator already executing"
            except ValueError:
                yield 1
        x = f()
        res = list(x)
        assert res == [1]

    def test_throw_on_finished_generator(self):
        def f():
            yield 1
        g = f()
        res = g.next()
        assert res == 1
        raises(StopIteration, g.next)
        raises(NameError, g.throw, NameError)

    def test_close(self):
        def f():
            yield 1
        g = f()
        assert g.close() is None

    def test_close2(self):
        def f():
            try:
                yield 1
            except GeneratorExit:
                raise StopIteration
        g = f()
        g.next()
        assert g.close() is None

    def test_close3(self):
        def f():
            try:
                yield 1
            except GeneratorExit:
                raise NameError
        g = f()
        g.next()
        raises(NameError, g.close)

    def test_close_fail(self):
        def f():
            try:
                yield 1
            except GeneratorExit:
                yield 2
        g = f()
        g.next()
        raises(RuntimeError, g.close)

    def test_close_on_collect(self):
        ## we need to exec it, else it won't run on python2.4
        d = {}
        exec """
        def f():
            try:
                yield
            finally:
                f.x = 42
        """.strip() in d

        g = d['f']()
        g.next()
        del g
        import gc
        gc.collect()
        assert d['f'].x == 42

    def test_generator_raises_typeerror(self):
        def f():
            yield 1
        g = f()
        raises(TypeError, g.send, 1)

    def test_generator_explicit_stopiteration(self):
        def f():
            yield 1
            raise StopIteration
        g = f()
        assert [x for x in g] == [1]

    def test_generator_propagate_stopiteration(self):
        def f():
            it = iter([1])
            while 1: yield it.next()
        g = f()
        assert [x for x in g] == [1]

    def test_generator_restart(self):
        def g():
            i = me.next()
            yield i
        me = g()
        raises(ValueError, me.next)

    def test_generator_expression(self):
        exec "res = sum(i*i for i in range(5))"
        assert res == 30

    def test_generator_expression_2(self):
        d = {}
        exec """
def f():
    total = sum(i for i in [x for x in z])
    return total, x
z = [1, 2, 7]
res = f()
""" in d
        assert d['res'] == (10, 7)

    def test_repr(self):
        def myFunc():
            yield 1
        g = myFunc()
        r = repr(g)
        assert r.startswith("<generator object myFunc at 0x")
        assert list(g) == [1]
        assert repr(g) == r

    def test_unpackiterable_gen(self):
        g = (i*i for i in range(-5, 3))
        assert set(g) == set([0, 1, 4, 9, 16, 25])
        assert set(g) == set()
        assert set(i for i in range(0)) == set()

    def test_explicit_stop_iteration_unpackiterable(self):
        def f():
            yield 1
            raise StopIteration
        assert tuple(f()) == (1,)