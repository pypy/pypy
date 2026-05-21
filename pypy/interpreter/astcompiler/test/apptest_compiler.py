import pytest


def _get_line_numbers(source, function=False):
    import dis
    code = compile(source, '<test>', 'exec')
    if function:
        code = code.co_consts[0]
    lines = [line for (start, line) in dis.findlinestarts(code)]
    if function:
        # Normalize relative to co_firstlineno (the def line).
        # CPython 3.11+ emits RESUME at co_firstlineno; PyPy does not.
        # Skip that entry so both produce the same sequence.
        base = code.co_firstlineno - 1
        lines = [l for l in lines if l != code.co_firstlineno]
    else:
        base = min(lines)
    return [line - base for line in lines]


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


def test_elim_jump_to_return():
    # CPython 3.11 keeps JUMP_FORWARD for "return x if cond else y".
    # We check that no JUMP_ABSOLUTE is emitted, matching CPython.
    import dis
    def f():
        return true_value if cond else false_value   # noqa: F821
    instrs = list(dis.get_instructions(f))
    opnames = [i.opname for i in instrs]
    assert 'JUMP_ABSOLUTE' not in opnames


def test_crash_ifelse_in_except():
    got = _get_line_numbers("""
def buggy():
    try:
        pass
    except OSError as exc:
        if a:
            pass
        elif b:
            pass
    else:
        f
""", function=True)
    assert got == [2, 3, 10, 4, 5, 6, 7, 8, 7, 6, 4]


def test_or_with_implicit_return():
    got = _get_line_numbers("""
def or_with_implicit_return():
    if a:
        (g
         or
         h)""", function=True)
    assert got == [2, 3, 5, 2]
