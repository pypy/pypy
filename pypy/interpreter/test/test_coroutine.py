
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
            next(cr.__await__())
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
            next(c.__await__())
        except StopIteration as e:
            assert e.value == 42
        else:
            assert False, "should have raised"
        assert seen == ['aenter', 'aexit']
        """
