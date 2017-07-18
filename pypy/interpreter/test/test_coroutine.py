
class AppTestCoroutine:

    def test_cannot_iterate(self): """
        async def f(x):
            pass
        raises(TypeError, "for i in f(5): pass")
        raises(TypeError, iter, f(5))
        raises(TypeError, next, f(5))
        """

    def test_async_for(self): """
        class X:
            def __aiter__(self):
                return MyAIter()
        class MyAIter:
            async def __anext__(self):
                return 42
        async def f(x):
            sum = 0
            async for a in x:
                sum += a
                if sum > 100:
                    break
            return sum
        cr = f(X())
        try:
            cr.send(None)
        except StopIteration as e:
            assert e.value == 42 * 3
        else:
            assert False, "should have raised"
        """

    def test_StopAsyncIteration(self): """
        class X:
            def __aiter__(self):
                return MyAIter()
        class MyAIter:
            count = 0
            async def __anext__(self):
                if self.count == 3:
                    raise StopAsyncIteration
                self.count += 1
                return 42
        async def f(x):
            sum = 0
            async for a in x:
                sum += a
            return sum
        cr = f(X())
        try:
            cr.send(None)
        except StopIteration as e:
            assert e.value == 42 * 3
        else:
            assert False, "should have raised"
        """

    def test_async_for_old_style(self): """
        class X:
            def __aiter__(self):
                return MyAIter()
        class MyAIter:
            def __await__(self):
                return iter([20, 30])
        async def f(x):
            sum = 0
            async for a in x:
                sum += a
                if sum > 100:
                    break
            return sum
        cr = f(X())
        assert next(cr.__await__()) == 20
        """

    def test_set_coroutine_wrapper(self): """
        import sys
        async def f():
            pass
        seen = []
        def my_wrapper(cr):
            seen.append(cr)
            return 42
        assert sys.get_coroutine_wrapper() is None
        sys.set_coroutine_wrapper(my_wrapper)
        assert sys.get_coroutine_wrapper() is my_wrapper
        cr = f()
        assert cr == 42
        sys.set_coroutine_wrapper(None)
        assert sys.get_coroutine_wrapper() is None
        """

    def test_async_with(self): """
        seen = []
        class X:
            async def __aenter__(self):
                seen.append('aenter')
            async def __aexit__(self, *args):
                seen.append('aexit')
        async def f(x):
            async with x:
                return 42
        c = f(X())
        try:
            c.send(None)
        except StopIteration as e:
            assert e.value == 42
        else:
            assert False, "should have raised"
        assert seen == ['aenter', 'aexit']
        """

    def test_await(self): """
        class X:
            def __await__(self):
                i1 = yield 40
                assert i1 == 82
                i2 = yield 41
                assert i2 == 93
        async def f():
            await X()
            await X()
        c = f()
        assert c.send(None) == 40
        assert c.send(82) == 41
        assert c.send(93) == 40
        assert c.send(82) == 41
        raises(StopIteration, c.send, 93)
        """

    def test_await_error(self): """
        async def f():
            await [42]
        c = f()
        try:
            c.send(None)
        except TypeError as e:
            assert str(e) == "object list can't be used in 'await' expression"
        else:
            assert False, "should have raised"
        """

    def test_async_with_exception_context(self): """
        class CM:
            async def __aenter__(self):
                pass
            async def __aexit__(self, *e):
                1/0
        async def f():
            async with CM():
                raise ValueError
        c = f()
        try:
            c.send(None)
        except ZeroDivisionError as e:
            assert e.__context__ is not None
            assert isinstance(e.__context__, ValueError)
        else:
            assert False, "should have raised"
        """

    def test_runtime_warning(self): """
        import gc, warnings
        async def foobaz():
            pass
        with warnings.catch_warnings(record=True) as l:
            foobaz()
            gc.collect()
            gc.collect()
            gc.collect()

        assert len(l) == 1, repr(l)
        w = l[0].message
        assert isinstance(w, RuntimeWarning)
        assert str(w).startswith("coroutine ")
        assert str(w).endswith("foobaz' was never awaited")
        """

    def test_async_for_with_tuple_subclass(self): """
        class Done(Exception): pass

        class AIter(tuple):
            i = 0
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self.i >= len(self):
                    raise StopAsyncIteration
                self.i += 1
                return self[self.i - 1]

        result = []
        async def foo():
            async for i in AIter([42]):
                result.append(i)
            raise Done

        try:
            foo().send(None)
        except Done:
            pass
        assert result == [42]
        """

    def test_async_yield(self): """
        class Done(Exception): pass

        async def mygen():
            yield 5

        result = []
        async def foo():
            async for i in mygen():
                result.append(i)
            raise Done

        try:
            foo().send(None)
        except Done:
            pass
        assert result == [5]
        """

    def test_async_yield_already_finished(self): """
        class Done(Exception): pass

        async def mygen():
            yield 5

        result = []
        async def foo():
            g = mygen()
            async for i in g:
                result.append(i)
            async for i in g:
                assert False   # should not be reached
            raise Done

        try:
            foo().send(None)
        except Done:
            pass
        assert result == [5]
        """

    def test_async_yield_with_await(self): """
        class Done(Exception): pass

        class X:
            def __await__(self):
                i1 = yield 40
                assert i1 == 82
                i2 = yield 41
                assert i2 == 93

        async def mygen():
            yield 5
            await X()
            yield 6

        result = []
        async def foo():
            async for i in mygen():
                result.append(i)
            raise Done

        co = foo()
        x = co.send(None)
        assert x == 40
        assert result == [5]
        x = co.send(82)
        assert x == 41
        assert result == [5]
        raises(Done, co.send, 93)
        assert result == [5, 6]
        """

    def test_async_yield_with_explicit_send(self): """
        class X:
            def __await__(self):
                i1 = yield 40
                assert i1 == 82
                i2 = yield 41
                assert i2 == 93

        async def mygen():
            x = yield 5
            assert x == 2189
            await X()
            y = yield 6
            assert y == 319

        result = []
        async def foo():
            gen = mygen()
            result.append(await gen.asend(None))
            result.append(await gen.asend(2189))
            try:
                await gen.asend(319)
            except StopAsyncIteration:
                return 42
            else:
                raise AssertionError

        co = foo()
        x = co.send(None)
        assert x == 40
        assert result == [5]
        x = co.send(82)
        assert x == 41
        assert result == [5]
        e = raises(StopIteration, co.send, 93)
        assert e.value.args == (42,)
        assert result == [5, 6]
        """

    def test_async_yield_explicit_asend_and_next(self): """
        async def mygen(y):
            assert y == 4983
            x = yield 5
            assert x == 2189
            yield "ok"

        g = mygen(4983)
        raises(TypeError, g.asend(42).__next__)
        e = raises(StopIteration, g.asend(None).__next__)
        assert e.value.args == (5,)
        e = raises(StopIteration, g.asend(2189).__next__)
        assert e.value.args == ("ok",)
        """

    def test_async_yield_explicit_asend_and_send(self): """
        async def mygen(y):
            assert y == 4983
            x = yield 5
            assert x == 2189
            yield "ok"

        g = mygen(4983)
        e = raises(TypeError, g.asend(None).send, 42)
        assert str(e.value) == ("can't send non-None value to a just-started "
                                "async generator")
        e = raises(StopIteration, g.asend(None).send, None)
        assert e.value.args == (5,)
        e = raises(StopIteration, g.asend("IGNORED").send, 2189)  # xxx
        assert e.value.args == ("ok",)
        """

    def test_async_yield_explicit_asend_used_several_times(self): """
        class X:
            def __await__(self):
                r = yield -2
                assert r == "cont1"
                r = yield -3
                assert r == "cont2"
                return -4
        async def mygen(y):
            x = await X()
            assert x == -4
            r = yield -5
            assert r == "foo"
            r = yield -6
            assert r == "bar"

        g = mygen(4983)
        gs = g.asend(None)
        r = gs.send(None)
        assert r == -2
        r = gs.send("cont1")
        assert r == -3
        e = raises(StopIteration, gs.send, "cont2")
        assert e.value.args == (-5,)
        e = raises(StopIteration, gs.send, None)
        assert e.value.args == ()
        e = raises(StopIteration, gs.send, None)
        assert e.value.args == ()
        #
        gs = g.asend("foo")
        e = raises(StopIteration, gs.send, None)
        assert e.value.args == (-6,)
        e = raises(StopIteration, gs.send, "bar")
        assert e.value.args == ()
        """

    def test_async_yield_asend_notnone_throw(self): """
        async def f():
            yield 123

        raises(ValueError, f().asend(42).throw, ValueError)
    """

    def test_async_yield_asend_none_throw(self): """
        async def f():
            yield 123

        raises(ValueError, f().asend(None).throw, ValueError)
    """

    def test_async_yield_athrow_send_none(self): """
        async def ag():
            yield 42

        raises(ValueError, ag().athrow(ValueError).send, None)
    """

    def test_async_yield_athrow_send_notnone(self): """
        async def ag():
            yield 42

        ex = raises(RuntimeError, ag().athrow(ValueError).send, 42)
        expected = ("can't send non-None value to a just-started coroutine", )
        assert ex.value.args == expected
        """

    def test_async_yield_athrow_throw(self): """
        async def ag():
            yield 42

        raises(RuntimeError, ag().athrow(ValueError).throw, LookupError)
        # CPython's message makes little sense; PyPy's message is different
    """

    def test_async_yield_athrow_while_running(self): """
        values = []
        async def ag():
            try:
                received = yield 1
            except ValueError:
                values.append(42)
                return
            yield 2


        async def run():
            running = ag()
            x = await running.asend(None)
            assert x == 1
            try:
                await running.athrow(ValueError)
            except StopAsyncIteration:
                pass


        try:
            run().send(None)
        except StopIteration:
            assert values == [42]
    """

    def test_async_aclose(self): """
        raises_generator_exit = False
        async def ag():
            nonlocal raises_generator_exit
            try:
                yield
            except GeneratorExit:
                raises_generator_exit = True
                raise

        async def run():
            a = ag()
            async for i in a:
                break
            await a.aclose()
        try:
            run().send(None)
        except StopIteration:
            pass
        assert raises_generator_exit
    """
