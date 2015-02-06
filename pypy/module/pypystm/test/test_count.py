

class AppTestCount:
    spaceconfig = dict(usemodules=['pypystm'])

    def test_count(self):
        import pypystm
        x = pypystm.count()
        y = pypystm.count()
        assert y == x + 1
