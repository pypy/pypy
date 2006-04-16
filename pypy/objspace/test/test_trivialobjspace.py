from pypy.conftest import gettestobjspace

class AppTest_Trivial:

    def setup_class(cls):
        cls.space = gettestobjspace('trivial')

    def test_pystone(self):
        from test import pystone
        try:
            pystone.main(1000)
        except ZeroDivisionError:
            pass    # null measured time
