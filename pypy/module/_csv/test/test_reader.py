from pypy.conftest import gettestobjspace


class AppTestReader(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_csv'])

        w__read_test = cls.space.appexec([], r"""():
            import _csv
            def _read_test(input, expect, **kwargs):
                reader = _csv.reader(input, **kwargs)
                if expect == 'Error':
                    raises(_csv.Error, list, reader)
                    return
                result = list(reader)
                assert result == expect, 'result: %r\nexpect: %r' % (
                    result, expect)
            return _read_test
        """)
        if type(w__read_test) is type(lambda:0):
            w__read_test = staticmethod(w__read_test)
        cls.w__read_test = w__read_test

    def test_simple_reader(self):
        self._read_test(['foo:bar\n'], [['foo', 'bar']], delimiter=':')

    def test_read_oddinputs(self):
        self._read_test([], [])
        self._read_test([''], [[]])
        self._read_test(['"ab"c'], 'Error', strict = 1)
        # cannot handle null bytes for the moment
        self._read_test(['ab\0c'], 'Error', strict = 1)
        self._read_test(['"ab"c'], [['abc']], doublequote = 0)
