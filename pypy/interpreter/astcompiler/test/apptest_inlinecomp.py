# Tests for PEP 709 inlined comprehensions: sync list/set/dict comps in a
# function whose child scopes are all such comprehensions.

def _run(src):
    ns = {}
    exec(compile(src, '<t>', 'exec'), ns)
    return ns

def _code_of(func):
    return func.__code__

def _opnames(func):
    import dis
    return [i.opname for i in dis.get_instructions(func)]

def test_listcomp_inlined_and_correct():
    ns = _run("def f():\n    return [x*2 for x in range(4)]\n")
    ops = _opnames(ns['f'])
    assert 'LIST_APPEND' in ops
    assert 'LOAD_FAST_AND_CLEAR' in ops
    assert 'MAKE_FUNCTION' not in ops
    assert ns['f']() == [0, 2, 4, 6]

def test_setcomp_dictcomp_inlined():
    ns = _run(
        "def fs():\n    return {x for x in range(3)}\n"
        "def fd():\n    return {k: k*k for k in range(3)}\n")
    assert 'SET_ADD' in _opnames(ns['fs'])
    assert 'MAP_ADD' in _opnames(ns['fd'])
    assert 'MAKE_FUNCTION' not in _opnames(ns['fs'])
    assert 'MAKE_FUNCTION' not in _opnames(ns['fd'])
    assert ns['fs']() == {0, 1, 2}
    assert ns['fd']() == {0: 0, 1: 1, 2: 4}

def test_comp_with_ifs():
    ns = _run("def f():\n    return [x for x in range(10) if x % 2 if x > 3]\n")
    assert ns['f']() == [5, 7, 9]

def test_comp_var_restored_bound():
    ns = _run(
        "def f():\n"
        "    x = 'outer'\n"
        "    r = [x for x in range(3)]\n"
        "    return r, x\n")
    assert ns['f']() == ([0, 1, 2], 'outer')

def test_comp_var_not_visible_after():
    # the read of y outside the comprehension resolves as a global
    ns = _run(
        "def f():\n"
        "    r = [y for y in range(2)]\n"
        "    try:\n"
        "        y\n"
        "    except NameError:\n"
        "        return r, 'invisible'\n"
        "    return r, 'leaked'\n")
    assert ns['f']() == ([0, 1], 'invisible')

def test_comp_reads_outer_fast():
    ns = _run(
        "def f():\n"
        "    n = 10\n"
        "    return [i + n for i in range(3)]\n")
    assert ns['f']() == [10, 11, 12]

def test_comp_then_try():
    ns = _run(
        "def g():\n"
        "    r = [y for y in range(2)]\n"
        "    try:\n"
        "        1/0\n"
        "    except ZeroDivisionError:\n"
        "        pass\n"
        "    return r\n")
    assert ns['g']() == [0, 1]

def test_comp_in_try():
    ns = _run(
        "def g():\n"
        "    try:\n"
        "        return [y for y in range(3)]\n"
        "    except Exception:\n"
        "        return None\n")
    assert ns['g']() == [0, 1, 2]

def test_exception_in_comp_restores_bound_target():
    ns = _run(
        "def f(it):\n"
        "    x = 'outer'\n"
        "    try:\n"
        "        r = [x for x in it]\n"
        "    except ValueError:\n"
        "        return x\n"
        "    return 'no error'\n")
    def boom():
        yield 1
        raise ValueError
    assert ns['f'](boom()) == 'outer'
    assert ns['f'](iter([1, 2])) == 'no error'

def test_exception_in_comp_restores_unbound_target():
    # the cleanup handler must restore the target slot to unbound, so it does
    # not show up in locals()
    ns = _run(
        "def f(it):\n"
        "    try:\n"
        "        r = [x for x in it]\n"
        "    except ValueError:\n"
        "        return 'x' in locals()\n"
        "    return 'no error'\n")
    def boom():
        yield 1
        raise ValueError
    assert ns['f'](boom()) is False

def test_genexp_not_inlined():
    ns = _run("def f():\n    return list(x for x in range(3))\n")
    assert 'MAKE_FUNCTION' in _opnames(ns['f'])
    assert ns['f']() == [0, 1, 2]

def _module_ops(src):
    import dis
    code = compile(src, '<t>', 'exec')
    return code, [i.opname for i in dis.get_instructions(code)]

def test_module_level_comp_inlined():
    code, ops = _module_ops("r = [x for x in range(3)]\n")
    assert 'LIST_APPEND' in ops
    assert 'LOAD_FAST_AND_CLEAR' in ops
    assert 'MAKE_FUNCTION' not in ops
    ns = {}
    exec(code, ns)
    assert ns['r'] == [0, 1, 2]
    assert 'x' not in ns

def test_module_level_comp_dict_disjoint():
    # the hidden comp slot never touches the module dict entry of the
    # same name, and a locals() sync must not delete it
    ns = _run(
        "x = 1\n"
        "r = [x for x in range(3)]\n"
        "locals()\n"
        "after = x\n")
    assert ns['r'] == [0, 1, 2]
    assert ns['x'] == 1
    assert ns['after'] == 1

def test_module_level_comp_reads_module_var():
    ns = _run(
        "n = 10\n"
        "r = [i + n for i in range(3)]\n")
    assert ns['r'] == [10, 11, 12]

def test_module_level_comp_with_sibling_def():
    ns = _run(
        "def g():\n"
        "    return x\n"
        "r = [x for x in range(3)]\n")
    assert ns['r'] == [0, 1, 2]
    try:
        ns['g']()
    except NameError:
        pass
    else:
        assert False, "x leaked to globals"

def test_module_level_walrus_escapes():
    ns = _run("r = [y := x for x in range(3)]\n")
    assert ns['r'] == [0, 1, 2]
    assert ns['y'] == 2

def test_module_level_exception_keeps_dict():
    ns = _run(
        "x = 5\n"
        "def boom():\n"
        "    yield 1\n"
        "    raise ValueError\n"
        "try:\n"
        "    r = [x for x in boom()]\n"
        "except ValueError:\n"
        "    pass\n"
        "after = x\n")
    assert ns['after'] == 5
    assert ns['x'] == 5

def test_class_body_comp_not_inlined():
    ns = _run(
        "class C:\n"
        "    r = [x for x in range(3)]\n")
    assert ns['C'].r == [0, 1, 2]

def test_sibling_closure_over_shared_name():
    # g closes over f's x (a cell); the comp target uses a hidden slot and
    # never touches the cell
    ns = _run(
        "def f():\n"
        "    x = 1\n"
        "    def g():\n"
        "        return x\n"
        "    r = [x for x in range(3)]\n"
        "    return g(), r, x\n")
    ops = _opnames(ns['f'])
    assert 'LIST_APPEND' in ops
    assert ns['f']() == (1, [0, 1, 2], 1)

def test_sibling_does_not_see_comp_private_name():
    # x exists in f only through the comp; in g it resolves as a global
    ns = _run(
        "def f():\n"
        "    def g():\n"
        "        return x\n"
        "    r = [x for x in range(3)]\n"
        "    return g, r\n")
    ops = _opnames(ns['f'])
    assert 'LIST_APPEND' in ops
    g, r = ns['f']()
    assert r == [0, 1, 2]
    try:
        g()
    except NameError:
        pass
    else:
        assert False, "expected NameError"
    ns['x'] = 99
    assert g() == 99

def test_comp_reads_sibling_cell():
    ns = _run(
        "def f():\n"
        "    x = 1\n"
        "    def g():\n"
        "        return x\n"
        "    r = [x + i for i in range(3)]\n"
        "    return r, g()\n")
    assert 'LIST_APPEND' in _opnames(ns['f'])
    assert ns['f']() == ([1, 2, 3], 1)

def test_lambda_sibling_allows_inlining():
    ns = _run(
        "def f():\n"
        "    h = lambda: 42\n"
        "    r = [q for q in range(3)]\n"
        "    return h(), r\n")
    assert 'LIST_APPEND' in _opnames(ns['f'])
    assert ns['f']() == (42, [0, 1, 2])

def test_genexp_sibling_allows_inlining():
    ns = _run(
        "def f():\n"
        "    ge = (q*2 for q in range(3))\n"
        "    r = [q for q in range(3)]\n"
        "    return list(ge), r\n")
    assert 'LIST_APPEND' in _opnames(ns['f'])
    assert ns['f']() == ([0, 2, 4], [0, 1, 2])

def test_comp_with_nested_lambda():
    ns = _run(
        "def f():\n"
        "    return [l() for l in [lambda: x for x in range(3)]]\n")
    assert ns['f']() == [2, 2, 2]

def test_walrus_inlined_and_escapes():
    ns = _run(
        "def f():\n"
        "    r = [y := x for x in range(3)]\n"
        "    return r, y\n")
    assert 'MAKE_FUNCTION' not in _opnames(ns['f'])
    assert ns['f']() == ([0, 1, 2], 2)

def test_use_only_conflict_hidden():
    # i is bound in the comp but only used in f: inside the comp it is a
    # fast-hidden slot, outside it still resolves as a global
    ns = _run(
        "def f():\n"
        "    s = {i for i in range(5)}\n"
        "    try:\n"
        "        return s, i\n"
        "    except NameError:\n"
        "        return s, 'global'\n")
    ops = _opnames(ns['f'])
    assert 'SET_ADD' in ops
    assert 'MAKE_FUNCTION' not in ops
    assert ns['f']() == ({0, 1, 2, 3, 4}, 'global')
    ns['i'] = 99
    assert ns['f']() == ({0, 1, 2, 3, 4}, 99)

def test_use_only_conflict_not_in_locals():
    ns = _run(
        "def f():\n"
        "    s = {i for i in range(5)}\n"
        "    return 'i' in locals()\n")
    assert ns['f']() is False

def test_parent_global_decl_conflict():
    ns = _run(
        "gx = 0\n"
        "def f():\n"
        "    global gx\n"
        "    gx = 5\n"
        "    r = [gx*2 for gx in range(3)]\n"
        "    return r, gx\n")
    assert 'MAKE_FUNCTION' not in _opnames(ns['f'])
    assert ns['f']() == ([0, 2, 4], 5)
    assert ns['gx'] == 5

def test_parent_nonlocal_decl_conflict():
    ns = _run(
        "def outer():\n"
        "    nx = 'o'\n"
        "    def inner():\n"
        "        nonlocal nx\n"
        "        nx = 'i'\n"
        "        r = [nx for nx in range(2)]\n"
        "        return r, nx\n"
        "    return inner(), nx\n")
    assert ns['outer']() == (([0, 1], 'i'), 'i')

def test_nested_comp():
    ns = _run(
        "def f():\n"
        "    return [[y for y in range(x)] for x in range(3)]\n")
    assert ns['f']() == [[], [0], [0, 1]]

def test_comp_result_used_in_expression():
    ns = _run(
        "def f():\n"
        "    return len([x for x in range(5)]) + max([x for x in range(5)])\n")
    assert ns['f']() == 9

def test_two_comps_same_target():
    ns = _run(
        "def f():\n"
        "    a = [x for x in range(2)]\n"
        "    b = [x*10 for x in range(2)]\n"
        "    return a, b\n")
    assert ns['f']() == ([0, 1], [0, 10])

def test_tuple_target_inlined():
    ns = _run(
        "def f():\n"
        "    a, b = 'A', 'B'\n"
        "    r = [a + b for a, b in [('x','y'), ('u','v')]]\n"
        "    return r, a, b\n")
    assert 'MAKE_FUNCTION' not in _opnames(ns['f'])
    assert ns['f']() == (['xy', 'uv'], 'A', 'B')

def test_starred_target_inlined():
    ns = _run(
        "def f():\n"
        "    return [(a, b) for a, *b in [(1, 2, 3), (4,)]]\n")
    assert ns['f']() == [(1, [2, 3]), (4, [])]

def test_multiple_generators_inlined():
    ns = _run(
        "def f():\n"
        "    return [x*10 + y for x in range(3) for y in range(2) if x != 1]\n")
    assert 'MAKE_FUNCTION' not in _opnames(ns['f'])
    assert ns['f']() == [0, 1, 20, 21]

def test_empty_tuple_target():
    ns = _run(
        "def f():\n"
        "    return [1 for () in [(), ()]]\n")
    assert ns['f']() == [1, 1]

def test_exception_restores_multiple_targets():
    ns = _run(
        "def f(it):\n"
        "    a, b = 'A', 'B'\n"
        "    try:\n"
        "        r = [a + b for a, b in it]\n"
        "    except ValueError:\n"
        "        return a, b\n"
        "    return 'no error'\n")
    def boom():
        yield ('x', 'y')
        raise ValueError
    assert ns['f'](boom()) == ('A', 'B')

ASYNC_PRELUDE = (
    "class AIter:\n"
    "    def __init__(self, items, raise_after=-1):\n"
    "        self.items = list(items)\n"
    "        self.raise_after = raise_after\n"
    "    def __aiter__(self):\n"
    "        return self\n"
    "    async def __anext__(self):\n"
    "        if self.raise_after == 0:\n"
    "            raise ValueError\n"
    "        self.raise_after -= 1\n"
    "        if not self.items:\n"
    "            raise StopAsyncIteration\n"
    "        return self.items.pop(0)\n"
)

def _drive(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise AssertionError("coroutine did not finish")

def test_async_listcomp_inlined():
    ns = _run(ASYNC_PRELUDE +
        "async def f():\n"
        "    return [x*2 async for x in AIter([1, 2, 3])]\n")
    ops = _opnames(ns['f'])
    assert 'LIST_APPEND' in ops
    assert 'MAKE_FUNCTION' not in ops
    assert _drive(ns['f']()) == [2, 4, 6]

def test_async_setcomp_dictcomp_inlined():
    ns = _run(ASYNC_PRELUDE +
        "async def fs():\n"
        "    return {x async for x in AIter([1, 2, 2])}\n"
        "async def fd():\n"
        "    return {k: k*k async for k in AIter([1, 2])}\n")
    assert 'MAKE_FUNCTION' not in _opnames(ns['fs'])
    assert _drive(ns['fs']()) == {1, 2}
    assert _drive(ns['fd']()) == {1: 1, 2: 4}

def test_async_comp_target_restored():
    ns = _run(ASYNC_PRELUDE +
        "async def f():\n"
        "    x = 'outer'\n"
        "    r = [x async for x in AIter([1, 2])]\n"
        "    return r, x\n")
    assert _drive(ns['f']()) == ([1, 2], 'outer')

def test_async_comp_exception_restores_target():
    ns = _run(ASYNC_PRELUDE +
        "async def f():\n"
        "    x = 'outer'\n"
        "    try:\n"
        "        r = [x async for x in AIter([1, 2, 3], raise_after=2)]\n"
        "    except ValueError:\n"
        "        return x\n"
        "    return 'no error'\n")
    assert _drive(ns['f']()) == 'outer'

def test_async_comp_in_sync_function_is_error():
    try:
        _run("def f():\n    return [x async for x in y]\n")
    except SyntaxError as e:
        assert 'asynchronous comprehension' in e.msg
    else:
        assert False, "expected SyntaxError"

def test_inner_async_generator_inlined():
    ns = _run(ASYNC_PRELUDE +
        "async def f():\n"
        "    return [(i, j) for i in range(2) async for j in AIter([7, 8])]\n")
    assert 'MAKE_FUNCTION' not in _opnames(ns['f'])
    assert _drive(ns['f']()) == [(0, 7), (0, 8), (1, 7), (1, 8)]

def test_eval_and_single_mode_comp():
    assert eval("[x*2 for x in range(3)]") == [0, 2, 4]
    ns = {}
    exec(compile("r = [x for x in range(3)]", '<t>', 'single'), ns)
    assert ns['r'] == [0, 1, 2]

def test_module_comp_positions():
    # spot-check the positions test_compile relies on: LIST_APPEND carries
    # the elt's span inside an inlined module-level comprehension
    import dis
    snippet = ("[(x,\n"
               "    2*x)\n"
               "    for x\n"
               "    in [1,2,3]]\n")
    code = compile(snippet, '<t>', 'exec')
    for ins in dis.get_instructions(code):
        if ins.opname == 'LIST_APPEND':
            p = ins.positions
            assert (p.lineno, p.end_lineno, p.col_offset, p.end_col_offset) == \
                   (1, 2, 1, 8)
            break
    else:
        assert False, "LIST_APPEND not found in module code"

def test_lambda_in_comp_inlined():
    ns = _run(
        "def f():\n"
        "    return [lambda: x for x in range(3)]\n")
    ops = _opnames(ns['f'])
    assert 'LIST_APPEND' in ops
    assert 'MAKE_CELL' in ops
    assert [l() for l in ns['f']()] == [2, 2, 2]
    assert ns['f']()[0].__qualname__ == 'f.<locals>.<lambda>'

def test_lambda_in_comp_fresh_cell_per_execution():
    ns = _run(
        "def g():\n"
        "    batches = []\n"
        "    for n in (3, 5):\n"
        "        batches.append([lambda: x for x in range(n)])\n"
        "    return [b[0]() for b in batches]\n")
    assert ns['g']() == [2, 4]

def test_lambda_in_comp_parent_bound_isolated():
    ns = _run(
        "def h():\n"
        "    x = 'outer'\n"
        "    r = [lambda: x for x in range(2)]\n"
        "    return r[0](), x\n")
    assert ns['h']() == (1, 'outer')

def test_lambda_in_comp_with_sibling_closure():
    ns = _run(
        "def k():\n"
        "    x = 1\n"
        "    def s():\n"
        "        return x\n"
        "    r = [lambda: x for x in range(2)]\n"
        "    return s(), r[0](), x\n")
    assert ns['k']() == (1, 1, 1)

def test_genexp_in_comp_inlined():
    ns = _run(
        "def m():\n"
        "    return [list(y*x for y in range(2)) for x in range(3)]\n")
    assert 'LIST_APPEND' in _opnames(ns['m'])
    assert ns['m']() == [[0, 0], [0, 1], [0, 2]]

def test_lambda_in_comp_closes_parent_local():
    # the lambda closes over both the comp target and a parent local; the
    # parent local must become a cell of the parent
    ns = _run(
        "def f():\n"
        "    n = 5\n"
        "    return [lambda: n + x for x in range(2)]\n")
    assert [l() for l in ns['f']()] == [6, 6]

def test_exception_in_cell_comp_restores():
    ns = _run(
        "def f(it):\n"
        "    x = 'outer'\n"
        "    def s():\n"
        "        return x\n"
        "    try:\n"
        "        r = [lambda: x for x in it]\n"
        "    except ValueError:\n"
        "        return s(), x\n"
        "    return 'no error'\n")
    def boom():
        yield 1
        raise ValueError
    assert ns['f'](boom()) == ('outer', 'outer')

def test_lambda_comp_target_not_in_locals():
    ns = _run(
        "def p():\n"
        "    [lambda: x for x in range(2)]\n"
        "    return 'x' in locals()\n")
    assert ns['p']() is False

def test_conflict_with_children_bails():
    # x is use-only in f but the comp (with a lambda child) binds it:
    # needs a hidden cell, so the old path is kept; semantics unchanged
    ns = _run(
        "def f():\n"
        "    r = [lambda: x for x in range(2)]\n"
        "    try:\n"
        "        return r[0](), x\n"
        "    except NameError:\n"
        "        return r[0](), 'global'\n")
    assert ns['f']() == (1, 'global')

def test_lambda_in_comp_inlined():
    ns = _run(
        "def f():\n"
        "    return [lambda: x for x in range(3)]\n")
    ops = _opnames(ns['f'])
    assert 'LIST_APPEND' in ops
    assert 'MAKE_CELL' in ops
    assert [l() for l in ns['f']()] == [2, 2, 2]
    assert ns['f']()[0].__qualname__ == 'f.<locals>.<lambda>'

def test_lambda_in_comp_fresh_cell_per_execution():
    ns = _run(
        "def g():\n"
        "    batches = []\n"
        "    for n in (3, 5):\n"
        "        batches.append([lambda: x for x in range(n)])\n"
        "    return [b[0]() for b in batches]\n")
    assert ns['g']() == [2, 4]

def test_lambda_in_comp_parent_bound_isolated():
    ns = _run(
        "def h():\n"
        "    x = 'outer'\n"
        "    r = [lambda: x for x in range(2)]\n"
        "    return r[0](), x\n")
    assert ns['h']() == (1, 'outer')

def test_lambda_in_comp_with_sibling_closure():
    ns = _run(
        "def k():\n"
        "    x = 1\n"
        "    def s():\n"
        "        return x\n"
        "    r = [lambda: x for x in range(2)]\n"
        "    return s(), r[0](), x\n")
    assert ns['k']() == (1, 1, 1)

def test_genexp_in_comp_inlined():
    ns = _run(
        "def m():\n"
        "    return [list(y*x for y in range(2)) for x in range(3)]\n")
    assert 'LIST_APPEND' in _opnames(ns['m'])
    assert ns['m']() == [[0, 0], [0, 1], [0, 2]]

def test_lambda_in_comp_closes_parent_local():
    # the lambda closes over both the comp target and a parent local; the
    # parent local must become a cell of the parent
    ns = _run(
        "def f():\n"
        "    n = 5\n"
        "    return [lambda: n + x for x in range(2)]\n")
    assert [l() for l in ns['f']()] == [6, 6]

def test_exception_in_cell_comp_restores():
    ns = _run(
        "def f(it):\n"
        "    x = 'outer'\n"
        "    def s():\n"
        "        return x\n"
        "    try:\n"
        "        r = [lambda: x for x in it]\n"
        "    except ValueError:\n"
        "        return s(), x\n"
        "    return 'no error'\n")
    def boom():
        yield 1
        raise ValueError
    assert ns['f'](boom()) == ('outer', 'outer')

def test_lambda_comp_target_not_in_locals():
    ns = _run(
        "def p():\n"
        "    [lambda: x for x in range(2)]\n"
        "    return 'x' in locals()\n")
    assert ns['p']() is False

def test_conflict_with_children_bails():
    # x is use-only in f but the comp (with a lambda child) binds it:
    # needs a hidden cell, so the old path is kept; semantics unchanged
    ns = _run(
        "def f():\n"
        "    r = [lambda: x for x in range(2)]\n"
        "    try:\n"
        "        return r[0](), x\n"
        "    except NameError:\n"
        "        return r[0](), 'global'\n")
    assert ns['f']() == (1, 'global')

def test_module_comp_var_in_frame_locals():
    import sys
    g = {'sys': sys}
    exec(compile("val = [sys._getframe().f_locals for a in [0]][0]['a']\n",
                 '<t>', 'exec'), g)
    assert g['val'] == 0
    assert 'a' not in g

def test_module_comp_var_in_locals_snapshot():
    g = {}
    exec(compile(
        "l = [1, 2]\n"
        "y = 0\n"
        "items = [locals()['x'] for x in l]\n"
        "items4 = [eval('x') for x in l]\n"
        "[exec('y = x') for x in l]\n", '<t>', 'exec'), g)
    assert g['items'] == [1, 2]
    assert g['items4'] == [1, 2]
    assert g['y'] == 0          # exec wrote to the snapshot, not the module
    assert 'x' not in g

def test_multiple_comprehension_name_reuse():
    # x bound by the first comp must not affect the second comp's resolution
    g = {'x': 3}
    exec(compile(
        "def _f():\n"
        "    [x for x in [1]]\n"
        "    y = [x for _ in [1]]\n"
        "    return y\n"
        "_out = _f()\n", '<t>', 'exec'), g)
    assert g['_out'] == [3]

def test_iterator_exception_positions():
    import dis
    code = compile("[x for x in gen_iter()]\n", '<t>', 'exec')
    for ins in dis.get_instructions(code):
        if ins.opname in ('GET_ITER', 'FOR_ITER'):
            p = ins.positions
            # the iterator expression is cols 12..22 on line 1
            assert (p.lineno, p.col_offset, p.end_col_offset) == (1, 12, 22), \
                   (ins.opname, p)
