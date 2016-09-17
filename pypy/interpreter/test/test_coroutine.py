
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
