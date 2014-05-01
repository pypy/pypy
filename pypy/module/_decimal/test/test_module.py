class AppTestDecimalModule:
    spaceconfig = dict(usemodules=('_decimal',))

    def test_constants(self):
        import _decimal
        assert _decimal.IEEE_CONTEXT_MAX_BITS > 3
