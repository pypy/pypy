from rpython.tool.sourcetools import (
    func_renamer, func_with_new_name, rpython_wrapper,
    getsourcelines, MyStr, newcode_withfilename, compile2)

def test_rename():
    def f(x, y=5):
        return x + y
    f.prop = int

    g = func_with_new_name(f, "g")
    assert g(4, 5) == 9
    assert g.__name__ == "g"
    assert f.__defaults__ == (5,)
    assert g.prop is int

def test_rename_decorator():
    @func_renamer("g")
    def f(x, y=5):
        return x + y
    f.prop = int

    assert f(4, 5) == 9

    assert f.__name__ == "g"
    assert f.__defaults__ == (5,)
    assert f.prop is int

def test_func_rename_decorator():
    def bar():
        'doc'

    bar2 = func_with_new_name(bar, 'bar2')
    assert bar.__doc__ == bar2.__doc__ == 'doc'

    bar.__doc__ = 'new doc'
    bar3 = func_with_new_name(bar, 'bar3')
    assert bar3.__doc__ == 'new doc'
    assert bar2.__doc__ != bar3.__doc__


def test_rpython_wrapper():
    calls = []

    def bar(a, b):
        calls.append(('bar', a, b))
        return a+b

    template = """
        def {name}({arglist}):
            calls.append(('decorated', {arglist}))
            return {original}({arglist})
    """
    bar = rpython_wrapper(bar, template, calls=calls)
    assert bar(40, 2) == 42
    assert calls == [
        ('decorated', 40, 2),
        ('bar', 40, 2),
        ]


# helper defined at module level so inspect.getsource can find it
def _sample_func_for_getsourcelines(x):
    return x + 1


def test_getsourcelines_normal_function():
    # getsourcelines returns (lines, startline) for a regular function defined
    # in a real file; startline matches co_firstlineno.
    result = getsourcelines(_sample_func_for_getsourcelines)
    assert result is not None
    lines, startline = result
    assert isinstance(lines, list)
    assert len(lines) > 0
    assert startline == _sample_func_for_getsourcelines.__code__.co_firstlineno
    joined = ''.join(lines)
    assert 'return x + 1' in joined


def test_getsourcelines_builtin_returns_none():
    # Built-ins have no __code__, so getsourcelines must return None.
    assert getsourcelines(len) is None


def test_getsourcelines_dynamic_function_returns_none():
    # Functions compiled from a string literal (no real source file) return None
    # rather than raising.
    import types
    code = compile('def f(x): return x', '<string>', 'exec')
    globs = {}
    exec code in globs
    f = globs['f']
    assert getsourcelines(f) is None

def test_getsourcelines_dynamic_function_compile2_works():
    # Functions compiled from a string literal compiled with compile2 can
    # produce a source line (this is the point of compile2, and why we use it
    # eg in the objspace).
    import types
    code = compile2('def f(x): return x', '<string>', 'exec')
    globs = {}
    exec code in globs
    f = globs['f']
    assert getsourcelines(f) == (['def f(x): return x\n'], 1)


def test_getsourcelines_sourceargs_substituted():
    # When co_filename is a MyStr with __sourceargs__, getsourcelines applies
    # the format args so callers see the resolved source, not the template.
    # Simulate what NiceCompile does: attach MyStr(real_filename, __sourceargs__)
    # to a freshly compiled code object.
    import __future__, types

    # We need the function to be "found" in this file via inspect, so we use
    # _sample_func_for_getsourcelines as the code carrier but swap its
    # co_filename for a MyStr that carries __sourceargs__.
    original_code = _sample_func_for_getsourcelines.__code__
    srcname = MyStr(original_code.co_filename)
    srcname.__sourceargs__ = ()   # empty: src % () == src (no substitution)
    patched_code = newcode_withfilename(original_code, srcname)
    import types as _types
    patched_func = _types.FunctionType(patched_code,
                                       _sample_func_for_getsourcelines.__globals__,
                                       '_sample_func_patched')

    result = getsourcelines(patched_func)
    assert result is not None
    lines, startline = result
    assert startline == patched_func.__code__.co_firstlineno
    assert 'return x + 1' in ''.join(lines)
