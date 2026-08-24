# spaceconfig = {"usemodules" : ["_functools"]}

from pytest import raises


def make_wrapper(func, maxsize=128, typed=False):
    from _functools import _lru_cache_wrapper
    from collections import namedtuple
    CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize",
                                          "currsize"])
    return _lru_cache_wrapper(func, maxsize, typed, CacheInfo)


def test_basic_hits_and_misses():
    calls = []
    def f(x):
        calls.append(x)
        return x * 2
    w = make_wrapper(f, maxsize=10)
    assert w(1) == 2
    assert w(2) == 4
    assert w(1) == 2
    assert calls == [1, 2]
    info = w.cache_info()
    assert (info.hits, info.misses, info.maxsize, info.currsize) == (
        1, 2, 10, 2)


def test_lru_eviction_order():
    calls = []
    def f(x):
        calls.append(x)
        return x * 2
    w = make_wrapper(f, maxsize=2)
    w(1)
    w(2)
    w(1)              # 1 is now most-recently-used, 2 is least
    w(3)              # cache full -> evicts 2, keeps 1 and 3
    assert calls == [1, 2, 3]
    w(1)              # still cached -> hit
    assert w.cache_info().hits == 2
    w(2)              # was evicted -> miss, recomputed
    assert calls == [1, 2, 3, 2]
    assert w.cache_info().misses == 4


def test_maxsize_none_is_unbounded():
    calls = []
    def f(x):
        calls.append(x)
        return x
    w = make_wrapper(f, maxsize=None)
    for i in range(500):
        w(i)
    for i in range(500):
        w(i)
    info = w.cache_info()
    assert info.maxsize is None
    assert info.misses == 500
    assert info.hits == 500
    assert info.currsize == 500


def test_maxsize_zero_disables_caching():
    calls = []
    def f(x):
        calls.append(x)
        return x
    w = make_wrapper(f, maxsize=0)
    w(9)
    w(9)
    info = w.cache_info()
    assert (info.hits, info.misses, info.maxsize, info.currsize) == (
        0, 2, 0, 0)
    assert calls == [9, 9]


def test_negative_maxsize_clamped_to_zero():
    calls = []
    def f(x):
        calls.append(x)
        return x
    w = make_wrapper(f, maxsize=-5)
    w(1)
    w(1)
    assert w.cache_info().maxsize == 0
    assert calls == [1, 1]


def test_typed_distinguishes_argument_types():
    calls = []
    def f(x):
        calls.append(x)
        return x
    w = make_wrapper(f, maxsize=10, typed=True)
    w(1)
    w(1.0)
    assert w.cache_info().misses == 2
    # even untyped, 1 and 1.0 never collide: a single int or str arg
    # gets a bare-key fast path, everything else (including float) is
    # wrapped in a sequence, and a wrapped key never equals a bare one.
    w_untyped = make_wrapper(f, maxsize=10, typed=False)
    w_untyped(1)
    w_untyped(1.0)
    assert w_untyped.cache_info().misses == 2
    w_untyped2 = make_wrapper(f, maxsize=10, typed=False)
    w_untyped2(1)
    w_untyped2(1)
    info = w_untyped2.cache_info()
    assert (info.hits, info.misses, info.currsize) == (1, 1, 1)


def test_kwargs_are_distinct_from_positional():
    calls = []
    def f(x):
        calls.append(x)
        return x
    w = make_wrapper(f, maxsize=10)
    w(1)
    w(x=1)
    assert calls == [1, 1]
    assert w.cache_info().misses == 2


def test_zero_arg_function():
    calls = []
    def f():
        calls.append(None)
        return 42
    w = make_wrapper(f, maxsize=10)
    assert w() == 42
    assert w() == 42
    info = w.cache_info()
    assert (info.hits, info.misses) == (1, 1)


def test_unhashable_argument_raises_typeerror():
    w = make_wrapper(lambda x: x, maxsize=10)
    raises(TypeError, w, [1, 2])


def test_cache_clear_resets_everything():
    calls = []
    def f(x):
        calls.append(x)
        return x
    w = make_wrapper(f, maxsize=10)
    w(1)
    w(1)
    w.cache_clear()
    info = w.cache_info()
    assert (info.hits, info.misses, info.currsize) == (0, 0, 0)
    w(1)
    assert calls == [1, 1]


def test_reentrant_call_with_same_key():
    # a call that, while computing its own result, re-enters the wrapper
    # with the exact same key before the outer call has stored anything
    calls = []
    def f(x):
        calls.append(x)
        if len(calls) == 1:
            return w(x) + 1
        return x * 10
    w = make_wrapper(f, maxsize=10)
    result = w(5)
    assert result == 51
    info = w.cache_info()
    assert (info.misses, info.currsize) == (2, 1)


def test_get_descriptor_on_a_method():
    class C(object):
        def method(self, x):
            return x + 1
        method = make_wrapper(method, maxsize=10)
    c = C()
    assert c.method(4) == 5
    assert c.method(4) == 5
    assert c.method.cache_info().hits == 1


def test_copy_and_deepcopy_return_self():
    import copy
    w = make_wrapper(lambda x: x, maxsize=10)
    assert w.__copy__() is w
    assert copy.deepcopy(w) is w


def test_has_instance_dict():
    w = make_wrapper(lambda x: x, maxsize=10)
    w.__wrapped__ = "marker"
    assert w.__wrapped__ == "marker"
    assert hasattr(w, '__dict__')
