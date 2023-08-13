import functools
import sys
import os

def test_partial_stack():
    # issue 3988
    stack = []
    def multiply(a, b):
        frame = sys._getframe()
        while frame:
            stack.append(frame.f_code.co_name)
            frame = frame.f_back
        return a * b

    penta = functools.partial(multiply, 5)
    assert penta(2) == 10
    assert len(stack) > 1
    # Make sure partial.__call__ is not in the first few stack functions
    assert all([f != "__call__" for f in stack[:3]])

def test_lru_cache_stack():
    # issue 3988
    stack = []
    @functools.lru_cache
    def multiply(a, b):
        frame = sys._getframe()
        while frame:
            stack.append(frame.f_code.co_name)
            frame = frame.f_back
        return a * b

    assert multiply(2, 5) == 10
    assert len(stack) > 1
    print(stack)
    # Make sure _lru_cache.wrapper is not in the first few stack functions
    assert all([f != "wrapper" for f in stack[:3]])

