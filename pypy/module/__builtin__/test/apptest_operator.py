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

def test_sync_anext_raises_exception():
    # A synchronous exception from __anext__ must propagate from anext()
    # itself, with or without a default (CPython gh-131670).
    for exc_type in [StopAsyncIteration, StopIteration, ValueError, Exception]:
        class A:
            def __anext__(self):
                raise exc_type('custom')
        with pytest.raises(exc_type):
            anext(A())
        with pytest.raises(exc_type):
            anext(A(), 1)

def test_anext_default_on_exhaustion():
    async def foo():
        yield 1

    async def run():
        it = aiter(foo())
        assert await anext(it, 'default') == 1
        assert await anext(it, 'default') == 'default'

    run_async(run())

def test_getattr_etc_error():
    with raises(TypeError) as info:
        getattr(test_getattr_etc_error, b'__code__')
    assert "attribute name must be string, not 'bytes'" in str(info.value)


