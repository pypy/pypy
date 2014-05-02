class AppTestExplicitConstruction:
    spaceconfig = dict(usemodules=('_decimal',))

    def test_explicit_empty(self):
        import _decimal
        Decimal = _decimal.Decimal
        assert Decimal() == Decimal("0")

