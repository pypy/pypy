from pypy.conftest import gettestobjspace


class AppTestReadline:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('readline',))
        cls.space = space

    def test_basic_import(self):
        import readline 
        readline.readline
        # test more 
