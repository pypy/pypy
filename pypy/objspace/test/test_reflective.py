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
        assert 1+2 == 42

        set_reflectivespace(None)
        assert 1+2 == 3
        
    def test_default_behaviour(self):
        from __pypy__ import set_reflectivespace
        class Space:
            pass

        set_reflectivespace(Space())
        assert 1+2 == 3
