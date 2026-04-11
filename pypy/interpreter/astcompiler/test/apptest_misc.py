import pytest
import warnings

def test_warning_to_error_translation():
    statement = """\
def wrong1():
    a = 1
    b = 2
    global a
    global b
"""
    with warnings.catch_warnings():
        warnings.filterwarnings("error", module="<test string>")
        try:
            compile(statement, '<test string>', 'exec')
        except SyntaxError as err:
            assert err.lineno is not None
            assert err.filename is not None
            assert err.offset is not None
            assert err.msg is not None

def test_error_message_ast():
    import ast
    pos = dict(lineno=2, col_offset=3)
    m = ast.Module([ast.Expr(ast.expr(**pos), **pos)], [])
    with pytest.raises(TypeError) as excinfo:
        compile(m, 'fn', 'exec')
    assert "expected some sort of expr, but got" in str(excinfo.value)

def test_weird_exec_bug():
    with pytest.raises(SyntaxError) as excinfo:
        compile('exec {1:(foo.)}', 'fn', 'exec')
    assert excinfo.value.offset == 6

def test_warning_decimal():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        compile("0x1for 2", "fn", "exec")
    assert len(w) == 1
    assert str(w[0].message) == "invalid hexadecimal literal"
    assert issubclass(w[0].category, SyntaxWarning)
    assert w[0].lineno == 1

    # Compiling with a SyntaxError may or may not emit the warning first
    # depending on the implementation (CPython does, PyPy does not).
    with warnings.catch_warnings(record=True) as w:
        with pytest.raises(SyntaxError):
            warnings.simplefilter("always")
            compile("0x1for 2 a b c", "fn", "exec")
    assert len(w) in (0, 1)

def test_warn_assert_tuple():
    for sourceline in ["assert(False, 'abc')", "assert(x, 'abc')"]:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compile(sourceline, "fn", "exec")
        assert len(w) == 1
        assert "perhaps remove parentheses" in str(w[0].message)
        assert w[0].lineno == 1

def test_warn_wrong_indices():
    for sourceline in ["(1, 2) [2, 3]", "(x, y) [a, b]"]:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compile(sourceline, "fn", "exec")
        assert len(w) == 1
        assert "indices must be" in str(w[0].message)
        assert w[0].lineno == 1

def test_error_position_unicode():
    source = "ááá ßßß úúú"
    try:
        compile(source, 'fn', 'exec')
    except SyntaxError as e:
        assert e.lineno == e.end_lineno == 1
        assert e.offset == 5
        assert e.end_offset == 8


def test_crash_debug():
    import ast
    tree = ast.parse("@deco1\n@deco2()\n@deco3(1)\ndef f(): pass")
    compile(tree, '<string>', 'exec')


def test_compile_nonascii_char_in_bytes_error():
    with pytest.raises(SyntaxError) as excinfo:
        compile("b = b'café'", "long-filename.py", "exec")
    assert excinfo.value.filename == "long-filename.py"
    assert excinfo.value.msg == "bytes can only contain ASCII literal characters"

def test_decorator_error_lineno():
    # The traceback for a failing decorator should point to the decorator
    # line, not the def line. See https://github.com/pypy/pypy/issues/5213
    import traceback

    def dec_error(func):
        raise TypeError("boom")
    def dec_fine(func):
        return func

    def applydecs():
        @dec_error      # line 12 relative to start of applydecs body
        @dec_fine
        def g(): pass

    try:
        applydecs()
    except TypeError:
        tb = traceback.extract_tb(__import__('sys').exc_info()[2])
    else:
        assert False, "expected TypeError"

    # find the frame for applydecs
    frame = [f for f in tb if f.name == 'applydecs']
    assert len(frame) == 1, frame
    # The line text should be the decorator, not the def
    assert frame[0].line is not None
    assert frame[0].line.strip().startswith('@dec_error'), (
        "expected decorator line, got: %r" % frame[0].line)


def test_decorated_function_store_on_def_line():
    # After applying all decorators, the STORE instruction for the function
    # name should be attributed to the 'def' line, not the outermost decorator.
    # This matches CPython's behaviour and makes sys.settrace count the def
    # line twice per decorated function definition.
    import sys

    src = """\
def id1(f): return f
def id2(f): return f
@id1
@id2
def g(): pass
"""
    ns = {}
    traced_lines = []
    code = compile(src, '<test_decorated_store>', 'exec')

    def tracer(frame, event, arg):
        if event == 'line' and frame.f_code is code:
            traced_lines.append(frame.f_lineno)
        return tracer

    sys.settrace(tracer)
    try:
        exec(code, ns)
    finally:
        sys.settrace(None)

    # line 5 is 'def g(): pass'
    # it should be traced twice: once for MAKE_FUNCTION and once for STORE_NAME
    assert traced_lines.count(5) == 2, (
        "expected 'def g' line (5) traced twice (MAKE_FUNCTION + STORE_NAME), "
        "got traced_lines=%r" % (traced_lines,))


def test_star_in_slice():
    class A:
        def __getitem__(self, index):
            return index
        def __setitem__(self, index, value):
            self.index = index
            self.value = value
        def __delitem__(self, index):
            self.delindex = index
    a = A()
    assert a[1] == 1
    assert a[*(1, 2, 3)] == (1, 2, 3)
    a[*(1, 2, 3)] = 12
    assert a.index == (1, 2, 3)
    del a[*(1, 2, 8)]
    assert a.delindex == (1, 2, 8)
