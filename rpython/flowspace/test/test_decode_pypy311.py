import sys

import pytest

if not (sys.version_info[:2] == (3, 11) and
        '__pypy__' in sys.builtin_module_names):
    pytest.skip("PyPy 3.11 bytecode", allow_module_level=True)

from rpython.flowspace import instr as I
from rpython.flowspace.decode_pypy311 import (
    OPMAP, EXTENDED_ARG, PyPy311Decoder, parse_exception_table)
from rpython.flowspace.objspace import build_flow


def decode(func):
    return PyPy311Decoder(func.__code__).decode()

def types_of(func):
    return [type(instr) for instr in decode(func).instrs]

def find(func, cls):
    return [instr for instr in decode(func).instrs if type(instr) is cls]

def function(source):
    """The function 'f' defined by a source that Python 2 cannot parse."""
    namespace = {}
    exec(source, namespace)
    return namespace['f']

def opnames(func):
    graph = build_flow(func)
    return [op.opname for block in graph.iterblocks()
            for op in block.operations]


class FakeCode(object):
    co_consts = [None, None, None]
    co_names = ['x', 'y', 'z']
    co_varnames = ('a', 'b', 'c')
    co_cellvars = ()
    co_freevars = ()
    co_exceptiontable = b''
    co_code = b''


NEED_CELLS = ('LOAD_CLOSURE', 'LOAD_DEREF', 'STORE_DEREF', 'DELETE_DEREF')
ALWAYS_REWRITTEN = ('CALL_FUNCTION_KW', 'CALL_METHOD_KW',
                    'BUILD_CONST_KEY_MAP', 'CALL_FUNCTION_EX')

@pytest.mark.parametrize('name', sorted(OPMAP))
def test_all_opcodes_decoded(name):
    if OPMAP[name] == EXTENDED_ARG:
        return
    if name in NEED_CELLS or name in ALWAYS_REWRITTEN:
        return
    decoder = PyPy311Decoder(FakeCode())
    for instr in PyPy311Decoder.opcodes[name](decoder, 2):
        assert isinstance(instr, I.Instr)


def test_jump_targets_are_positions():
    def f(x, y):
        total = 0
        for i in range(x):
            if i > y:
                total += i
            elif i == 3:
                continue
            while total > 100:
                total -= y
        return total
    code = decode(f)
    offsets = [instr.offset for instr in code.instrs]
    assert offsets == sorted(offsets)
    jumps = [instr for instr in code.instrs if isinstance(instr, I.JumpInstr)]
    assert any(type(instr) is I.ForIter for instr in jumps)
    assert any(instr.target <= code.instrs.index(instr) for instr in jumps)
    for instr in jumps:
        assert 0 <= instr.target < len(code.instrs)


def test_extended_arg():
    numbers = list(range(1000, 1400))
    source = 'def f(x):\n    return [x, %s]\n' % ', '.join(map(str, numbers))
    loaded = [instr.value for instr in find(function(source), I.LoadConst)]
    assert loaded == numbers


def test_linetable():
    def f(x):
        y = x + 1

        return y
    code = decode(f)
    first = f.__code__.co_firstlineno
    lines = [code.linetable.offset2lineno(instr.offset)
             for instr in code.instrs]
    assert lines[0] == first + 1
    assert lines[-1] == first + 3
    assert lines == sorted(lines)
    assert code.linetable.offset2lineno(-1) == first


def test_star_call():
    def f(g, a, b, c):
        return g(a, b, *c)
    assert types_of(f) == [I.LoadFast] * 4 + [I.Call, I.ReturnValue]
    assert find(f, I.Call) == [I.Call(2, (), True)]
    assert opnames(f) == ['call_args']

def test_star_call_only():
    def f(g, c):
        return g(*c)
    assert find(f, I.Call) == [I.Call(0, (), True)]

def test_star_call_keywords():
    def f(g, a, c, d):
        return g(a, k=d, *c)
    assert find(f, I.Call) == [I.Call(1, ('k',), True)]
    assert I.LoadConst(('k',)) not in decode(f).instrs
    assert opnames(f) == ['call_args']

def test_star_call_with_branches():
    def f(g, a, b, c, d):
        return g(a if d else b, *(c or d), k=(a if b else c))
    assert find(f, I.Call) == [I.Call(1, ('k',), True)]
    assert not find(f, I.BuildList)
    assert not find(f, I.Unsupported)
    assert 'newlist' not in opnames(f)

def test_nested_star_calls():
    def f(g, a, b, c):
        return g(a, *g(b, *c))
    assert find(f, I.Call) == [I.Call(1, (), True), I.Call(1, (), True)]
    assert not find(f, I.Unsupported)

def test_list_display_is_kept():
    def f(g, a, c):
        return g([a], *c)
    assert find(f, I.BuildList) == [I.BuildList(1)]
    assert find(f, I.Call) == [I.Call(1, (), True)]

def test_unsupported_unpacking():
    for expr in ['(a, *c)', '[a, *c]', 'g(*c, a)', 'g(*a, *c)', 'g(**c)']:
        f = function('def f(g, a, c):\n    return %s\n' % expr)
        assert find(f, I.Unsupported)

def test_keyword_calls():
    def f(g, o, a, b):
        g(a, k=b)
        return o.m(a, b, j=a, k=b)
    assert find(f, I.Call) == [I.Call(1, ('k',)), I.Call(2, ('j', 'k'))]
    assert I.LoadConst(('k',)) not in decode(f).instrs
    assert find(f, I.LoadAttr) == [I.LoadAttr('m')]

def test_const_key_map():
    def f(a, b):
        return {'x': a, 'y': b}
    assert find(f, I.BuildConstKeyMap) == [I.BuildConstKeyMap(('x', 'y'))]
    assert opnames(f) == ['newdict', 'setitem', 'setitem']

def test_slices():
    def f(a, x, y, v):
        a[x:y] = v
        del a[:y]
        return a[x:]
    assert find(f, I.StoreSlice) == [I.StoreSlice(True, True)]
    assert find(f, I.DeleteSlice) == [I.DeleteSlice(True, True)]
    assert find(f, I.GetSlice) == [I.GetSlice(True, True)]
    assert not find(f, I.BuildSlice)
    assert opnames(f) == ['setslice', 'delslice', 'getslice']

def test_slice_with_step():
    def f(a, x):
        return a[x::2]
    assert find(f, I.BuildSlice) == [I.BuildSlice(True)]
    assert opnames(f) == ['newslice', 'getitem']


def test_comprehension_is_inlined():
    def f(xs):
        return [x + 1 for x in xs]
    code = decode(f)
    assert code.varnames == ['xs', '.0', 'x']
    assert code.nlocals == 3
    assert not find(f, I.MakeFunction)
    assert len(find(f, I.ReturnValue)) == 1
    assert find(f, I.StoreFast) == [I.StoreFast(1), I.StoreFast(2)]
    for instr in code.instrs:
        if isinstance(instr, I.JumpInstr):
            assert 0 <= instr.target < len(code.instrs)
    names = opnames(f)
    assert names.count('simple_call') == 1
    assert names.count('iter') == names.count('next') == 1

def test_comprehension_cells_are_locals():
    def f(xs, n):
        m = n + 1
        return [x + n + m for x in xs]
    code = decode(f)
    assert code.varnames == ['xs', 'n', 'm', '.0', 'x']
    assert not find(f, I.LoadDeref)
    assert I.StoreFast(2) in code.instrs
    assert I.LoadFast(2) in code.instrs

def test_comprehension_reads_free_variable():
    def make(k):
        def f(xs):
            return [x + k for x in xs]
        return f
    f = make(5)
    code = decode(f)
    assert code.freevars == ['k']
    assert find(f, I.LoadDeref) == [I.LoadDeref(0)]

def test_nested_comprehensions():
    def f(xss, n):
        return [[x + n for x in xs] for xs in xss]
    code = decode(f)
    assert code.varnames == ['xss', 'n', '.0', 'xs', '.0', 'x']
    assert len(find(f, I.ForIter)) == 2
    assert len(find(f, I.ReturnValue)) == 1
    graph = build_flow(f)
    assert len(graph.getargs()) == 2

def test_two_comprehensions():
    def f(xs, ys):
        return [x for x in xs], [y for y in ys if y]
    code = decode(f)
    assert code.varnames == ['xs', 'ys', '.0', 'x', '.0', 'y']
    build_flow(f)

def test_closures_are_rejected():
    def f(n):
        return lambda x: x + n
    def g(xs, n):
        return list(x + n for x in xs)
    for func in f, g:
        with pytest.raises(ValueError) as excinfo:
            decode(func)
        assert "closures" in str(excinfo.value)

def test_other_comprehensions_are_unsupported():
    def f(xs, n):
        return {x: n for x in xs}
    def g(xs, n):
        return {x + n for x in xs}
    assert find(f, I.Unsupported) == [
        I.Unsupported("dict comprehensions is not RPython")]
    assert find(g, I.Unsupported) == [
        I.Unsupported("set comprehensions is not RPython")]


def test_parse_exception_table():
    def f(g):
        try:
            g()
        except ValueError:
            return 1
    entries = parse_exception_table(f.__code__.co_exceptiontable)
    size = len(f.__code__.co_code)
    assert entries
    for start, end, target, depth, lasti in entries:
        assert 0 <= start < end <= size
        assert 0 <= target < size
        assert start % 2 == end % 2 == target % 2 == 0
    assert entries[0][3:] == (0, False)

def test_handlers():
    def f(g, a):
        try:
            g(a)
        except ValueError as e:
            return e
    code = decode(f)
    handler = code.find_handler(2)
    assert type(code.instrs[handler.target]) is I.PushExcInfo
    assert handler.catches
    assert handler.depth == 0
    assert code.find_handler(len(code.instrs) - 1) is None
    cleanup = code.find_handler(handler.target)
    assert type(code.instrs[cleanup.target]) is I.Copy
    assert not cleanup.catches
    assert find(f, I.StoreException) == [I.StoreException(2)]

def test_cleanup_handler_inside_finally_catches():
    def f(g, a):
        try:
            try:
                g(a)
            except ValueError:
                g(a)
        finally:
            a.x = 1
    code = decode(f)
    inner = code.find_handler(2)
    cleanup = code.find_handler(inner.target)
    assert type(code.instrs[cleanup.target]) is I.Copy
    assert cleanup.catches

def test_exceptions_only_guessed_inside_try():
    def f(g, a):
        g(a)
        try:
            g(a)
        except ValueError:
            g(a)
        return g(a)
    graph = build_flow(f)
    raising = [block for block in graph.iterblocks() if block.canraise]
    assert len(raising) == 1

def test_with():
    def f(m, g):
        with m as x:
            g(x)
    assert len(find(f, I.BeforeWith)) == 1
    assert len(find(f, I.WithExceptStart)) == 1
    names = opnames(f)
    assert names.count('getattr') == 2

def test_raise_from():
    f = function('def f(x, y):\n    raise ValueError(x) from y\n')
    assert types_of(f)[-2:] == [I.PopTop, I.Py2Raise]

def test_make_function():
    def f():
        def g(a, b=3):
            return a
        return g
    assert len(find(f, I.MakeFunctionWithDefaults)) == 1
    graph = build_flow(f)
    g = graph.startblock.exits[0].args[0].value
    assert g(1) == 1 and g.__defaults__ == (3,)

def test_stack_depths():
    def f(g, a, b):
        for x in a:
            try:
                with b:
                    g(x, *a, k=[y for y in b])
            finally:
                g(a[1:2])
        return g
    decoder = PyPy311Decoder(f.__code__)
    depths = [host.depth for host in decoder.host_instrs]
    assert None not in depths
    assert min(depths) == 0
    assert max(depths) <= f.__code__.co_stacksize
