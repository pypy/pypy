import py
from pypy.conftest import gettestobjspace, runappdirect

class AppTest(object):
    def setup_class(cls):
        if runappdirect:
            py.test.skip("does not make sense on pypy-c")
        cls.space = gettestobjspace(**{"objspace.usemodules.select": False})

    def test__isfake(self):
        from pypymagic import isfake
        assert not isfake(map)
        assert not isfake(object)
        assert not isfake(isfake)

    def test__isfake_currently_true(self):
        from pypymagic import isfake
        import select
        assert isfake(select)
