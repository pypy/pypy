
class AppTestCoroutine:

    def test_cannot_iterate(self): """
        async def f(x):
            pass
        raises(TypeError, "for i in f(5): pass")
        raises(TypeError, iter, f(5))
        raises(TypeError, next, f(5))
        """
