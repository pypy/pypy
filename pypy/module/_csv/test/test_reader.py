from pypy.conftest import gettestobjspace


class AppTestReader(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_csv'])

    def test_simple_reader(self):
        import _csv
        r = _csv.reader(['foo:bar\n'], delimiter=':')
        lst = list(r)
        assert lst == [['foo', 'bar']]
