from pytest import raises
import warnings

def test_bytes_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=DeprecationWarning)
        eval("b'''\n\\z'''")
    assert len(w) == 1
    assert w[0].filename == '<string>'
    assert w[0].lineno == 1

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=DeprecationWarning)
        with raises(SyntaxError) as excinfo:
            eval("b'''\n\\z'''")
    assert not w
    assert excinfo.value.filename == '<string>'
    assert excinfo.value.lineno == 1

def test_str_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=DeprecationWarning)
        eval("'''\n\\z'''")
    assert len(w) == 1
    assert w[0].filename == '<string>'
    assert w[0].lineno == 1

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=DeprecationWarning)
        with raises(SyntaxError) as excinfo:
            eval("'''\n\\z'''")
    assert not w
    assert excinfo.value.filename == '<string>'
    assert excinfo.value.lineno == 1

def test_str_invalid_octal_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=DeprecationWarning)
        eval("'''\n\\407'''")
    assert len(w) == 1
    assert str(w[0].message) == r"invalid octal escape sequence '\407'"

def test_fstring_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=DeprecationWarning)
        eval('f"\\{8}"')
    assert len(w) == 1
    assert w[0].filename == '<string>'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=DeprecationWarning)
        with raises(SyntaxError) as excinfo:
            eval('f"\\{8}"')
    assert not w
    assert excinfo.value.filename == '<string>'

def test_invalid_escape_syntax_error_span():
    # When -Werror promotes the DeprecationWarning to a SyntaxError, the
    # error should highlight the full string token, not just one character.
    # E.g. for '"""\q"""' (8 chars) the end offset must be start+8.
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=DeprecationWarning)
        with raises(SyntaxError) as excinfo:
            eval('"""\\q"""')
    assert not w
    exc = excinfo.value
    # offset is 1-based column of opening quote; end_offset covers
    # the full token '"""\q"""' (8 chars).
    assert exc.end_offset - exc.offset == len('"""\\q"""')

def test_invalid_escape_plus_syntax_error_single_warning():
    # When a string literal contains an invalid escape sequence AND the
    # surrounding expression is a SyntaxError, the DeprecationWarning must
    # be emitted exactly once. The call_invalid_rules second parse pass must
    # not re-emit it.
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=DeprecationWarning)
        try:
            compile("'\\e' 1", '<test>', 'single')
        except SyntaxError:
            pass
    dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(dep) == 1, dep
