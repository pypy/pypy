import pytest


def test_nonlocal_class_nesting_bug():
    def foo():
        var = 0
        class C:
            def wrapper():
                nonlocal var
                var = 1
            wrapper()
            nonlocal var
        return var
    assert foo() == 1


def test_if_call_or_call_bug():
    # used to crash the compiler
    a = True
    calls = []
    def f1(): calls.append('f1')
    def g1(): calls.append('g1')
    if a:
        (f1() or
         g1())
    assert calls == ['f1', 'g1']   # f1 returns None (falsy), so g1 runs
    calls = []
    if a:
        (f1() and
         g1())
    assert calls == ['f1']          # f1 returns None (falsy), g1 short-circuits


def test_match_optimize_default():
    def f(x):
        match x:
            case 1:
                return 1
            case _:
                return 2
    assert f(1) == 1
    assert f(99) == 2
