from .support import HPyTest


class TestImporting(HPyTest):

    def test_importing_attributes(self):
        import pytest
        if not self.supports_ordinary_make_module_imports():
            pytest.skip()
        mod = self.make_module("""
            @INIT
        """, name='mytest')
        assert mod.__name__ == 'mytest'
        assert mod.__package__ == ''
        assert mod.__doc__ == 'some test for hpy'
        assert mod.__loader__.name == 'mytest'
        assert mod.__spec__.loader is mod.__loader__
        assert mod.__spec__.name == 'mytest'
        assert mod.__file__
