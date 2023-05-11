import pytest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.conftest import option

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


