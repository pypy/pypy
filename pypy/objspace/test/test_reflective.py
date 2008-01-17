from pypy.conftest import gettestobjspace

class AppTest_Reflective:

    def setup_class(cls):
        cls.space = gettestobjspace('reflective')

    def test_add(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def add(self, x, y):
                return 40+2

        set_reflectivespace(Space())
        x = 1
        y = 2
        assert x + y == 42

        set_reflectivespace(None)
        assert 1+2 == 3
        
    def test_default_behaviour(self):
        from __pypy__ import set_reflectivespace
        class Space:
            pass

        set_reflectivespace(Space())
        x = 1
        y = 2
        assert x + y == 3

    def test_newdict(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def newdict(self, d):
                d['surprise'] = 42
                return d

        set_reflectivespace(Space())
        d = {"b": 1}
        assert d["surprise"] == 42
        set_reflectivespace(None)


    def test_newlist(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def newlist(self, l):
                l.append(len(l))
                return l

        set_reflectivespace(Space())
        l = [1, 2, 3, 4, 5]
        assert len(l) == 6
        set_reflectivespace(None)
