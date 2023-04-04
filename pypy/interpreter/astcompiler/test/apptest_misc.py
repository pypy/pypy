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
    assert w[0].lineno == 1

    # don't warn if there's an error
    with warnings.catch_warnings(record=True) as w:
        with pytest.raises(SyntaxError):
            warnings.simplefilter("always")
            compile("0x1for 2 a b c", "fn", "exec")
    assert len(w) == 0

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


