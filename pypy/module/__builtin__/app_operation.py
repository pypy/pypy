import _operator

def bin(x):
    """Return the binary representation of an integer.

    >>> bin(2796202)
    '0b1010101010101010101010'

    """
    value = _operator.index(x)
    return value.__format__("#b")

def oct(x):
    """Return the octal representation of an integer.

    >>> oct(342391)
    '0o1234567'

    """
    x = _operator.index(x)
    return x.__format__("#o")

def hex(x):
    """Return the hexadecimal representation of an integer.

    >>> hex(12648430)
    '0xc0ffee'

    """
    x = _operator.index(x)
    return x.__format__("#x")


# anext and aiter adapted from: https://github.com/python/cpython/pull/8895

_NOT_PROVIDED = object()  # sentinel object to detect when a kwarg was not given


def aiter(obj):
    """aiter(async_iterable) -> async_iterator
    aiter(async_callable, sentinel) -> async_iterator
    Like the iter() builtin but for async iterables and callables.
    """
    typ = type(obj)
    try:
        meth = typ.__aiter__
    except AttributeError:
        raise TypeError(f"'{type(obj).__name__}' object is not an async iterable")
    ait = meth(obj)
    if not hasattr(ait, '__anext__'):
        raise TypeError(f"aiter() returned not an async iterator of type '{type(ait).__name__}'")
    return ait

def anext(iterator, default=_NOT_PROVIDED):
    """anext(async_iterator[, default])
    Return the next item from the async iterator.
    If default is given and the iterator is exhausted,
    it is returned instead of raising StopAsyncIteration.
    """
    typ = type(iterator)

    try:
        __anext__ = typ.__anext__
    except AttributeError:
        raise TypeError(f"'{type(iterator).__name__}' object is not an async iterator")

    if default is _NOT_PROVIDED:
        return __anext__(iterator)

    async def anext_impl():
        try:
            # The C code is way more low-level than this, as it implements
            # all methods of the iterator protocol. In this implementation
            # we're relying on higher-level coroutine concepts, but that's
            # exactly what we want -- crosstest pure-Python high-level
            # implementation and low-level C anext() iterators.
            return await __anext__(iterator)
        except StopAsyncIteration:
            return default

    return anext_impl()


