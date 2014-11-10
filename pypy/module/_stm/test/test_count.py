

class AppTestCount:
    spaceconfig = dict(usemodules=['_stm'])

    def test_count(self):
        import _stm
        x = _stm.count()
        y = _stm.count()
        assert y == x + 1
