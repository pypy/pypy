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


def test_finally_lineno_wrong():
    ns = {}
    exec("""def f(x): # 1
    def f(func):
        return func
    return f

@f(1)
def finally_wrong_lineno():
    try: # 8
        return print(1) # 9
    finally:
        print(2) # 11
    print(3) # 12
import dis
co = finally_wrong_lineno.__code__
linestarts = list(dis.findlinestarts(co))
x = [lineno for addr, lineno in linestarts]
""", ns)
    assert ns['x'] == [8, 9, 11]


def test_lineno1_eval_bug():
    ns = {}
    exec("""c = compile('z', '<string>', 'eval')
import dis
x = [lineno for addr, lineno in dis.findlinestarts(c)]
""", ns)
    assert ns['x'] == [1]


def test_with_lineno_wrong():
    ns = {}
    exec("""def with_wrong_lineno():
    with ABC():
        g()
import dis
co = with_wrong_lineno.__code__
linestarts = list(dis.findlinestarts(co))
x = [lineno for addr, lineno in linestarts]
""", ns)
    assert ns['x'] == [2, 3, 2]


def test_bug_lnotab():
    ns = {}
    exec("""
def buggy_lnotab():
    for i in x:







        1
x = [c for c in buggy_lnotab.__code__.co_lnotab]
""", ns)
    assert ns['x'] == [0, 1, 8, 8, 2, 248]


def test_lnotab_backwards_in_expr():
    ns = {}
    exec("""
def expr_lines(x):
    return (x +
        1)
x = [c for c in expr_lines.__code__.co_lnotab]
""", ns)
    assert ns['x'] == [0, 1, 2, 1, 2, 255]


def test_lineno_docstring_class():
    ns = {}
    exec("""
def expr_lines(x):
    class A:
        "abc"
x = [c for c in expr_lines.__code__.co_consts[1].co_lnotab]
""", ns)
    assert ns['x'] == [8, 1]


def test_lineno_funcdef():
    ns = {}
    exec('''def f():
    @decorator
    def my_function(
        x=x
    ):
        pass
x = [c for c in f.__code__.co_lnotab]
''', ns)
    assert ns['x'] == [0, 1, 2, 2, 2, 255, 6, 255, 2, 1]


def test_lineno_crash():
    ns = {}
    exec('''
def ie(c, r, fg, cc):
    tc = True if cc is False else c in Cc and r in Rc
    if tc:
        (print("wut") if fg is not None
         else None)
import dis
co = ie.__code__
linestarts = list(dis.findlinestarts(co))
x = [lineno for addr, lineno in linestarts]
''', ns)
    assert ns['x'] == [3, 4, 5, 6, 4]


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
    assert _position_of(src, lambda i: i.opname == 'BEFORE_WITH') == (2, 2, 9, 12)
    assert _position_of(src, lambda i: i.opname == 'POP_TOP') == (2, 2, 9, 12)


def _code_position_of(code, opname, occurrence=1):
    import dis
    n = occurrence
    for instr, pos in zip(dis.get_instructions(code), code.co_positions()):
        if instr.opname == opname:
            n -= 1
            if not n:
                return pos
    raise AssertionError('no %s found' % opname)


def test_jump_position_is_tested_expr():
    import textwrap
    code = compile(textwrap.dedent("""\
        if (a or
            (b and not c) or
            not (
                d > 0)):
            x = 42
        """), '<test>', 'exec')
    assert _code_position_of(code, 'POP_JUMP_IF_TRUE', 1) == (1, 1, 4, 5)
    assert _code_position_of(code, 'POP_JUMP_IF_FALSE', 1) == (2, 2, 5, 6)
    assert _code_position_of(code, 'POP_JUMP_IF_FALSE', 2) == (2, 2, 15, 16)
    assert _code_position_of(code, 'COMPARE_OP', 1) == (4, 4, 8, 13)
    assert _code_position_of(code, 'POP_JUMP_IF_TRUE', 2) == (4, 4, 8, 13)


def test_comprehension_element_positions():
    import textwrap
    body = textwrap.dedent("""\
        %s(x,
            2*x)
            for x
            in [1,2,3] if (x > 0
                           and x < 100
                           and x != 50)%s
        """)
    for start, end, opname in [('(', ')', 'YIELD_VALUE'),
                               ('[', ']', 'LIST_APPEND'),
                               ('{', '}', 'SET_ADD')]:
        code = compile(body % (start, end), '<test>', 'exec').co_consts[0]
        assert _code_position_of(code, opname) == (1, 2, 1, 8)
        assert _code_position_of(code, 'JUMP_ABSOLUTE') == (1, 2, 1, 8)
        assert _code_position_of(code, 'FOR_ITER') == (4, 4, 7, 14)
        assert _code_position_of(code, 'POP_JUMP_IF_FALSE', 1) == (4, 4, 19, 24)
    # the implicit return after the loop inherits the iterable's position
    code = compile(body % ('(', ')'), '<test>', 'exec').co_consts[0]
    assert _code_position_of(code, 'RETURN_CONST') == (4, 4, 7, 14)

    code = compile(textwrap.dedent("""\
        {x:
            2*x
            for x
            in [1,2,3] if (x > 0
                           and x < 100
                           and x != 50)}
        """), '<test>', 'exec').co_consts[0]
    assert _code_position_of(code, 'MAP_ADD') == (1, 2, 1, 7)
    assert _code_position_of(code, 'JUMP_ABSOLUTE') == (1, 2, 1, 7)


def test_async_comprehension_positions():
    import textwrap, types
    code = compile(textwrap.dedent("""\
        async def f():
            [(x,
                2*x)
                async for x
                in [1,2,3] if (x > 0
                               and x < 100
                               and x != 50)]
        """), '<test>', 'exec')
    g = {}
    eval(code, g)
    code = [c for c in g['f'].__code__.co_consts if isinstance(c, types.CodeType)][0]
    assert _code_position_of(code, 'LIST_APPEND') == (2, 3, 5, 12)
    assert _code_position_of(code, 'JUMP_ABSOLUTE') == (2, 3, 5, 12)
    assert _code_position_of(code, 'PUSH_EXC_INFO') == (2, 7, 4, 36)
    assert _code_position_of(code, 'RETURN_VALUE') == (2, 7, 4, 36)


def test_genexp_line_numbers():
    def return_genexp():
        return (1
                for
                x
                in
                y)
    code = return_genexp.__code__.co_consts[1]
    last_line = -2
    res = []
    for _, _, line in code.co_lines():
        if line is not None and line != last_line:
            res.append(line - code.co_firstlineno)
            last_line = line
    assert res == [0, 4, 2, 0, 4]


def test_match_pattern_positions():
    import textwrap
    code = compile(textwrap.dedent("""\
        match x:
            case a, *b, c:
                pass
        """), '<test>', 'exec')
    # UNPACK_EX needs an EXTENDED_ARG here, which must not lose the position
    assert _code_position_of(code, 'EXTENDED_ARG') == (2, 2, 9, 17)
    assert _code_position_of(code, 'UNPACK_EX') == (2, 2, 9, 17)
    assert _code_position_of(code, 'STORE_NAME', 3) == (2, 2, 9, 17)

    code = compile(textwrap.dedent("""\
        match x:
            case C(1) | C(2):
                pass
        """), '<test>', 'exec')
    assert _code_position_of(code, 'MATCH_CLASS', 1) == (2, 2, 9, 13)
    assert _code_position_of(code, 'COMPARE_OP', 1) == (2, 2, 11, 12)
    assert _code_position_of(code, 'MATCH_CLASS', 2) == (2, 2, 16, 20)
    assert _code_position_of(code, 'COMPARE_OP', 2) == (2, 2, 18, 19)


def test_for_loop_iter_exception_position():
    # Exceptions raised from __iter__() or __next__() while running a
    # for-loop should be attributed to the iterable expression's own line,
    # not to the whole for-loop (which would span down into the body, e.g.
    # to the "pass" line below).
    class BrokenIter:
        def __init__(self, next_raises=False, iter_raises=False):
            self.next_raises = next_raises
            self.iter_raises = iter_raises
        def __iter__(self):
            if self.iter_raises:
                raise ValueError
            return self
        def __next__(self):
            if self.next_raises:
                raise ValueError
            raise StopIteration

    def next_raises():
        try:
            for x in BrokenIter(next_raises=True):
                pass
        except Exception as e:
            return e

    def iter_raises():
        try:
            for x in BrokenIter(iter_raises=True):
                pass
        except Exception as e:
            return e

    for func in (next_raises, iter_raises):
        exc = func()
        tb = exc.__traceback__
        code = tb.tb_frame.f_code
        lineno, end_lineno, col, end_col = list(code.co_positions())[tb.tb_lasti // 2]
        assert lineno == code.co_firstlineno + 2
        assert end_lineno == code.co_firstlineno + 2


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
