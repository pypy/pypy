import token

def test_isterminal():
    assert token.ISTERMINAL(token.ENDMARKER)
    assert not token.ISTERMINAL(300)

def test_isnonterminal():
    assert token.ISNONTERMINAL(300)
    assert not token.ISNONTERMINAL(token.NAME)

def test_iseof():
    assert token.ISEOF(token.ENDMARKER)
    assert not token.ISEOF(token.NAME)

def test_nl_and_comment_exist_in_all():
    assert "NL" in token.__all__
    assert "COMMENT" in token.__all__

def test_encoding_exists():
    assert token.ISTERMINAL(token.ENCODING)

def test_exact_token_types():
    assert token.EXACT_TOKEN_TYPES[":="] == token.COLONEQUAL

def test_old_not_equal_is_gone():
    assert "<>" not in token.EXACT_TOKEN_TYPES
    assert "!=" in token.EXACT_TOKEN_TYPES
    assert token.EXACT_TOKEN_TYPES["!="] == token.NOTEQUAL

def test_soft_keyword_exists():
    assert token.ISTERMINAL(token.SOFT_KEYWORD)
