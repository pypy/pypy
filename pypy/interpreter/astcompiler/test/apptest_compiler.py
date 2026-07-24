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


def test_compile_ast_object_pep695_type_alias():
    # PEP 695 TypeAlias test
    from _ast import PyCF_ONLY_AST
    for src in ("type X = int\n", "type Stack[T] = list[T]\n"):
        tree = compile(src, "<test>", "exec", PyCF_ONLY_AST)
        compile(tree, "<test>", "exec")


def test_extended_arg_keeps_source_position():
    # An instruction needing an EXTENDED_ARG prefix (here UNPACK_EX for
    # 'a, *b, c', oparg (1<<8)|1 == 257) must keep its source position on the
    # real opcode, not only on the EXTENDED_ARG.
    import dis
    import textwrap
    snippet = textwrap.dedent("""\
        match x:
            case a, *b, c:
                pass
        """)
    code = compile(snippet, "<test>", "exec")
    for ins in dis.get_instructions(code):
        if ins.opname == "UNPACK_EX":
            p = ins.positions
            assert (p.lineno, p.end_lineno, p.col_offset, p.end_col_offset) == \
                   (2, 2, 9, 17)
            break
    else:
        assert False, "UNPACK_EX not found"


def test_backward_jump_has_lineno():
    # CPython gh-107901: backward jumps must carry a line number
    import dis
    def f():
        for i in x:      # noqa: F821
            if y:        # noqa: F821
                pass
    linenos = [ins.positions.lineno
               for ins in dis.get_instructions(f.__code__)
               if ins.opname == 'JUMP_ABSOLUTE']
    assert len(linenos) > 0
    assert all(l is not None for l in linenos)
