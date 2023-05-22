import pytest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.conftest import option


@pytest.mark.skip("too slow, over 30 seconds for this one test")
class AppTestAsyncIter(AppTestCpythonExtensionBase):
    enable_leak_checking = True

    def test_asyncgen(self):
        """ module is this code after running through cython
            async def test_gen():
                a = yield 123
                assert a is None
                yield 456
                yield 789

            def run_until_complete(coro):
                while True:
                    try:
                        fut = coro.send(None)
                    except StopIteration as ex:
                        return ex.args[0]

            def to_list(gen):
                async def iterate():
                    res = []
                    async for i in gen:
                        res.append(i)
                    return res

                return run_until_complete(iterate())
            """
        module = self.import_module(name='test_asyncgen')
        result = module.to_list(module.test_gen())
        assert result == [123, 456, 789]


    def test_async_gen_exception_04(self):
        """module is this code after running through cython, then making some
           small adjustments (see https://github.com/cython/cython/pull/5429)
            ZERO = 0

            async def gen():
                yield 123
                1 / ZERO

            def test_last_yield(g):
                ai = g.__aiter__()
                an = ai.__anext__()
                try:
                    next(an) 
                except StopIteration as ex:
                    return ex.args
                else:
                    return None 
             
        """
        module = self.import_module(name='test_async_gen_exception_04')
        g = module.gen()
        result = module.test_last_yield(g)
        assert result == 123 
