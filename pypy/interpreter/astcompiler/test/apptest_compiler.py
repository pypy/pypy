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


def _position_of(source, matches, occurrence=1):
    # Find the co_positions() entry of the nth instruction (1-based) in the
    # top-level function of `source` for which matches(instr) is true, with
    # line/end_line normalized relative to co_firstlineno (so the result
    # doesn't depend on where the def happens to sit in the source string).
    import dis
    code = compile(source, '<test>', 'exec').co_consts[0]
    base = code.co_firstlineno - 1
    n = occurrence
    for instr, pos in zip(dis.get_instructions(code, show_caches=True),
                           code.co_positions()):
        if matches(instr):
            n -= 1
            if not n:
                line, end_line, col, end_col = pos
                if line is not None:
                    line -= base
                if end_line is not None:
                    end_line -= base
                return (line, end_line, col, end_col)
    raise AssertionError('no matching instruction found')


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


def test_compile_ast_object_pep695_type_alias():
    # PEP 695 TypeAlias test
    from _ast import PyCF_ONLY_AST
    for src in ("type X = int\n", "type Stack[T] = list[T]\n"):
        tree = compile(src, "<test>", "exec", PyCF_ONLY_AST)
        compile(tree, "<test>", "exec")


def test_load_method_position_is_method_name():
    # LOAD_METHOD should get the position of the method name,
    # not the position of the object.
    pos = _position_of("""
def fmeth():       # line 1
    (              # line 2
        o.         # line 3
        m          # line 4
    )()            # line 5
""", lambda i: i.opname == 'LOAD_METHOD')
    assert pos == (4, 4, 8, 9)


def test_augassign_attribute_position_is_attr_name():
    # LOAD_ATTR and STORE_ATTR in augmented assignment should get the
    # position of the attribute name, not the object.
    src = """
def faug():        # line 1
    (              # line 2
        o.         # line 3
        a          # line 4
    ) += 1         # line 5
"""
    load_pos = _position_of(src, lambda i: i.opname == 'LOAD_ATTR')
    store_pos = _position_of(src, lambda i: i.opname == 'STORE_ATTR')
    assert load_pos == (4, 4, 8, 9)
    assert store_pos == (4, 4, 8, 9)


def test_with_cleanup_position_is_context_expr():
    # The implicit __exit__(None, None, None) cleanup emitted for a `with`
    # block should get the position of the context expression, not the
    # position of the whole `with` statement (which would span the entire
    # body, e.g. down to a `return` several lines later).
    src = """
def f():          # line 1
    with xyz:     # line 2
        1         # line 3
        2         # line 4
        return R  # line 5
"""
    # PyPy emits a single LOAD_CONST(None) followed by two DUP_TOP for the
    # three None arguments; CPython emits three separate LOAD_CONST(None).
    # Check both share the context expression's position either way.
    is_load_none = lambda i: i.opname == 'LOAD_CONST' and i.argval is None
    assert _position_of(src, is_load_none) == (2, 2, 9, 12)
    assert _position_of(src, lambda i: i.opname == 'RETURN_VALUE') == (2, 2, 9, 12)
    assert _position_of(src, lambda i: i.opname == 'RETURN_VALUE') == (2, 2, 9, 12)


def test_exception_table_after_early_return_block():
    values = {}

    def f(obj):
        try:
            if ((getattr(obj, "a", None) and
                    getattr(obj, "b", None)) or
                    getattr(obj, "c", None)):
                return 0.1
            return values[None]
        except KeyError:
            return 1.0

    assert f(object()) == 1.0
