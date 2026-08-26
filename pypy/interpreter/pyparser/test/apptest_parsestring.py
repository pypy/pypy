from pytest import raises
import warnings

def test_bytes_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=SyntaxWarning)
        eval("b'''\n\\z'''")
    assert len(w) == 1
    assert w[0].filename == '<string>'
    assert w[0].lineno == 1

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=SyntaxWarning)
        with raises(SyntaxError) as excinfo:
            eval("b'''\n\\z'''")
    assert not w
    assert excinfo.value.filename == '<string>'
    assert excinfo.value.lineno == 1

def test_str_invalid_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=SyntaxWarning)
        eval("'''\n\\z'''")
    assert len(w) == 1
    assert w[0].filename == '<string>'
    # the \z is on the second physical line of the triple-quoted string
    assert w[0].lineno == 2

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=SyntaxWarning)
        with raises(SyntaxError) as excinfo:
            eval("'''\n\\z'''")
    assert not w
    assert excinfo.value.filename == '<string>'
    assert excinfo.value.lineno == 2

def test_str_invalid_octal_escape():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=DeprecationWarning)
        eval("'''\n\\407'''")
    assert len(w) == 1
    assert str(w[0].message) == r"invalid octal escape sequence '\407'"

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

def test_invalid_escape_syntax_error_span():
    # When -Werror promotes the SyntaxWarning to a SyntaxError, the error
    # should highlight just the escape sequence itself (backslash + one
    # char), matching CPython, not the whole string token.
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('error', category=SyntaxWarning)
        with raises(SyntaxError) as excinfo:
            eval('"""\\q"""')
    assert not w
    exc = excinfo.value
    # '"""\q"""': the backslash is at 0-based col 3, i.e. 1-based offset 4.
    assert exc.offset == 4
    assert exc.end_offset == 6

def test_invalid_escape_plus_syntax_error_single_warning():
    # When a string literal contains an invalid escape sequence AND the
    # surrounding expression is a SyntaxError, the SyntaxWarning must
    # be emitted exactly once. The call_invalid_rules second parse pass must
    # not re-emit it.
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always', category=SyntaxWarning)
        try:
            compile("'\\e' 1", '<test>', 'single')
        except SyntaxError:
            pass
    warn = [x for x in w if issubclass(x.category, SyntaxWarning)]
    assert len(warn) == 1, str(warn)
