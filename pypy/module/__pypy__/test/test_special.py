import py
from pypy.conftest import gettestobjspace, option

class AppTest(object):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("does not make sense on pypy-c")
        cls.space = gettestobjspace(**{"objspace.usemodules.select": False})

    def test__isfake(self):
        from __pypy__ import isfake
        assert not isfake(map)
        assert not isfake(object)
        assert not isfake(isfake)

    def test__isfake_currently_true(self):
        from __pypy__ import isfake
        import select
        assert isfake(select)
