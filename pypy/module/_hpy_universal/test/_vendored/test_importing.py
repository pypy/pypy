import sys
import pytest
from .support import HPyTest

# PyPy tests are always run with python2
ISPYPY = sys.version_info[0] < 3

if not ISPYPY:
    @pytest.fixture(params=['cpython', 'universal', 'hybrid', 'debug'])
    def hpy_abi(request):
        abi = request.param
        yield abi


class TestImporting(HPyTest):

    def full_import(self, name, mod_filename):
        import importlib
        import sys
        import os
        if name in sys.modules:
            raise ValueError(
                "Test module {!r} already present in sys.modules".format(name))
        importlib.invalidate_caches()
        mod_dir = os.path.dirname(mod_filename)
        sys.path.insert(0, mod_dir)
        try:
            module = importlib.import_module(name)
            assert sys.modules[name] is module
        finally:
            # assert that the module import didn't change the sys.path entry
            # that was added above, then remove the entry.
            assert sys.path[0] == mod_dir
            del sys.path[0]
            if name in sys.modules:
                del sys.modules[name]
        return module

    def test_importing_attributes(self):
        import pytest
        if not self.supports_ordinary_make_module_imports():
            pytest.skip()
        from hpy.devel.abitag import get_hpy_ext_suffix
        mod = self.make_module("""
            @INIT
        """, name='mytest')
        mod = self.full_import(mod.__name__, mod.__file__)
        assert mod.__name__ == 'mytest'
        assert mod.__package__ == ''
        assert mod.__doc__ == 'some test for hpy'
        assert mod.__loader__.name == 'mytest'
        assert mod.__spec__.loader is mod.__loader__
        assert mod.__spec__.name == 'mytest'
        assert mod.__file__

        hpy_abi = self.compiler.hpy_abi
        if hpy_abi == 'debug':
            hpy_abi = 'universal'
        ext_suffix = get_hpy_ext_suffix(hpy_abi)
        assert repr(mod) == '<module \'mytest\' from {}>'.format(
            repr(str(self.compiler.tmpdir.join('mytest' + ext_suffix))))
