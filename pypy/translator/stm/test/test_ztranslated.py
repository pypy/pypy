import py
from pypy.translator.stm.test.support import CompiledSTMTests
from pypy.translator.stm.test import targetdemo


class TestSTMTranslated(CompiledSTMTests):

    def test_hello_world(self):
        t, cbuilder = self.compile(targetdemo.entry_point)
        data, dataerr = cbuilder.cmdexec('4 5000', err=True)
        assert 'done sleeping.' in dataerr
        assert 'check ok!' in data
