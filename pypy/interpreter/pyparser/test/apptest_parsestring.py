from pytest import raises
import warnings

def test_bytes_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=SyntaxWarning)
        eval("b'''\n\\z'''")
    assert len(w) == 1
    assert w[0].filename == '<string>'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=SyntaxWarning)
        with raises(SyntaxError) as excinfo:
            eval("b'''\n\\z'''")
    assert not w
    assert excinfo.value.filename == '<string>'

def test_str_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=SyntaxWarning)
        eval("'''\n\\z'''")
    assert len(w) == 1
    assert w[0].filename == '<string>'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=SyntaxWarning)
        with raises(SyntaxError) as excinfo:
            eval("'''\n\\z'''")
    assert not w
    assert excinfo.value.filename == '<string>'

def test_fstring_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=SyntaxWarning)
        eval('f"\\{8}"')
    assert len(w) == 1
    assert w[0].filename == '<string>'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=SyntaxWarning)
        with raises(SyntaxError) as excinfo:
            eval('f"\\{8}"')
    assert not w
    assert excinfo.value.filename == '<string>'
