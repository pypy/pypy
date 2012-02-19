import py
from pypy.translator.stm.test.support import CompiledSTMTests
from pypy.translator.stm.test import targetdemo


class TestSTMTranslated(CompiledSTMTests):

    def test_hello_world(self):
        t, cbuilder = self.compile(targetdemo.entry_point)
        data = cbuilder.cmdexec('4 5000')
        assert 'done sleeping.' in data
        assert 'check ok!' in data
