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
