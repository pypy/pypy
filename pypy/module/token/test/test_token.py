class AppTestToken:

    def setup_class(cls):
        cls.w_token = cls.space.appexec([], """():
    import token
    return token""")

    def test_isterminal(self):
        assert self.token.ISTERMINAL(self.token.ENDMARKER)
        assert not self.token.ISTERMINAL(300)

    def test_isnonterminal(self):
        assert self.token.ISNONTERMINAL(300)
        assert not self.token.ISNONTERMINAL(self.token.NAME)

    def test_iseof(self):
        assert self.token.ISEOF(self.token.ENDMARKER)
        assert not self.token.ISEOF(self.token.NAME)
