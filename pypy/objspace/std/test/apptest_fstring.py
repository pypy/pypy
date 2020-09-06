# spaceconfig = {"usemodules" : ["unicodedata"]}
import ast
import warnings

def test_error_unknown_code():
    def fn():
        f'{1000:j}'
    exc_info = raises(ValueError, fn)
    assert str(exc_info.value).startswith("Unknown format code")

def test_ast_lineno_and_col_offset():
    m = ast.parse("\nf'a{x}bc{y}de'")
    x_ast = m.body[0].value.values[1].value
    y_ast = m.body[0].value.values[3].value
    assert x_ast.lineno == 2
    assert x_ast.col_offset == 4
    assert y_ast.lineno == 2
    assert y_ast.col_offset == 9

def test_ast_lineno_and_col_offset_unicode():
    s = "\nf'α{χ}βγ{ψ}δε'"
    assert s.encode('utf-8') ==b"\nf'\xce\xb1{\xcf\x87}\xce\xb2\xce\xb3{\xcf\x88}\xce\xb4\xce\xb5'"
    m = ast.parse(s)
    x_ast = m.body[0].value.values[1].value
    y_ast = m.body[0].value.values[3].value
    assert x_ast.lineno == 2
    assert x_ast.col_offset == 5
    assert y_ast.lineno == 2
    assert y_ast.col_offset == 13

def test_ast_mutiline_lineno_and_col_offset():
    m = ast.parse("\n\nf'''{x}\nabc{y}\n{\nz}'''   \n\n\n")
    x_ast = m.body[0].value.values[0].value
    y_ast = m.body[0].value.values[2].value
    z_ast = m.body[0].value.values[4].value
    assert x_ast.lineno == 3
    assert x_ast.col_offset == 5
    assert y_ast.lineno == 4
    assert y_ast.col_offset == 5
    assert z_ast.lineno == 6
    assert z_ast.col_offset == 0

def test_double_braces():
    assert f'{{' == '{'
    assert f'a{{' == 'a{'
    assert f'{{b' == '{b'
    assert f'a{{b' == 'a{b'
    assert f'}}' == '}'
    assert f'a}}' == 'a}'
    assert f'}}b' == '}b'
    assert f'a}}b' == 'a}b'
    assert f'{{}}' == '{}'
    assert f'a{{}}' == 'a{}'
    assert f'{{b}}' == '{b}'
    assert f'{{}}c' == '{}c'
    assert f'a{{b}}' == 'a{b}'
    assert f'a{{}}c' == 'a{}c'
    assert f'{{b}}c' == '{b}c'
    assert f'a{{b}}c' == 'a{b}c'

    assert f'{{{10}' == '{10'
    assert f'}}{10}' == '}10'
    assert f'}}{{{10}' == '}{10'
    assert f'}}a{{{10}' == '}a{10'

    assert f'{10}{{' == '10{'
    assert f'{10}}}' == '10}'
    assert f'{10}}}{{' == '10}{'
    assert f'{10}}}a{{' '}' == '10}a{}'

    # Inside of strings, don't interpret doubled brackets.
    assert f'{"{{}}"}' == '{{}}'

    exc_info = raises(TypeError, eval, "f'{ {{}} }'")  # dict in a set
    assert 'unhashable' in str(exc_info.value)

def test_backslashes_in_string_part():
    assert f'\t' == '\t'
    assert r'\t' == '\\t'
    assert rf'\t' == '\\t'
    assert f'{2}\t' == '2\t'
    assert f'{2}\t{3}' == '2\t3'
    assert f'\t{3}' == '\t3'

    assert f'\u0394' == '\u0394'
    assert r'\u0394' == '\\u0394'
    assert rf'\u0394' == '\\u0394'
    assert f'{2}\u0394' == '2\u0394'
    assert f'{2}\u0394{3}' == '2\u03943'
    assert f'\u0394{3}' == '\u03943'

    assert f'\U00000394' == '\u0394'
    assert r'\U00000394' == '\\U00000394'
    assert rf'\U00000394' == '\\U00000394'
    assert f'{2}\U00000394' == '2\u0394'
    assert f'{2}\U00000394{3}' == '2\u03943'
    assert f'\U00000394{3}' == '\u03943'

    assert f'\N{GREEK CAPITAL LETTER DELTA}' == '\u0394'
    assert f'{2}\N{GREEK CAPITAL LETTER DELTA}' == '2\u0394'
    assert f'{2}\N{GREEK CAPITAL LETTER DELTA}{3}' == '2\u03943'
    assert f'\N{GREEK CAPITAL LETTER DELTA}{3}' == '\u03943'
    assert f'2\N{GREEK CAPITAL LETTER DELTA}' == '2\u0394'
    assert f'2\N{GREEK CAPITAL LETTER DELTA}3' == '2\u03943'
    assert f'\N{GREEK CAPITAL LETTER DELTA}3' == '\u03943'

    assert f'\x20' == ' '
    assert r'\x20' == '\\x20'
    assert rf'\x20' == '\\x20'
    assert f'{2}\x20' == '2 '
    assert f'{2}\x20{3}' == '2 3'
    assert f'\x20{3}' == ' 3'

    assert f'2\x20' == '2 '
    assert f'2\x203' == '2 3'
    assert f'\x203' == ' 3'

    with warnings.catch_warnings(record=True) as w:  # invalid escape sequence
        warnings.simplefilter("always", DeprecationWarning)
        value = eval(r"f'\{6*7}'")
        assert len(w) == 1 and w[0].category == DeprecationWarning
    assert value == '\\42'
    assert f'\\{6*7}' == '\\42'
    assert fr'\{6*7}' == '\\42'

    AMPERSAND = 'spam'
    # Get the right unicode character (&), or pick up local variable
    # depending on the number of backslashes.
    assert f'\N{AMPERSAND}' == '&'
    assert f'\\N{AMPERSAND}' == '\\Nspam'
    assert fr'\N{AMPERSAND}' == '\\Nspam'
    assert f'\\\N{AMPERSAND}' == '\\&'
