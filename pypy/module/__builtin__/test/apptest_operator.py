import pytest

def run_async(coro):
    buffer = []
    result = None
    while True:
        try:
            buffer.append(coro.send(None))
        except StopIteration as ex:
            result = ex.args[0] if ex.args else None
            break
    return buffer, result

def test_error_aiter_anext():
    with pytest.raises(TypeError) as info:
        aiter(1)
    assert "'int' object is not an async iterable" in str(info.value)

    with pytest.raises(TypeError) as info:
        anext(1)
    assert "'int' object is not an async iterator" in str(info.value)

    class BadAsyncIterable:
        def __aiter__(self):
            return 'abc'

    with pytest.raises(TypeError) as info:
        aiter(BadAsyncIterable())
    assert "aiter() returned not an async iterator of type 'str'" in str(info.value)


def test_aiter_anext():
    async def foo():
        yield 1
        yield 2

    async def run():
        it = aiter(foo())
        val1 = await anext(it)
        assert val1 == 1
        val2 = await anext(it)
        assert val2 == 2

    run_async(run())

