import pytest
from .support import HPyTest

# this function should probably goes somewhere into hpy.universal and/or and
# hpy package and/or an import hook, or whatever. I do not want to think about
# this now.
def import_module_properly(mod):
    raise NotImplementedError("fix me eventually")

# this was moved from support.py, where it did not belong
## class HPyLoader(ExtensionFileLoader):
##     def create_module(self, spec):
##         import hpy.universal
##         return hpy.universal.load_from_spec(spec)


class TestImporting(HPyTest):

    @pytest.mark.xfail
    def test_importing_attributes(self):
        import sys
        modname = 'mytest'
        so_filename = self.compile_module("""
            @INIT
        """, name=modname)
        mod = import_module_properly(so_filename, modname)
        assert mod in sys.modules
        assert mod.__loader__.name == 'mytest'
        assert mod.__spec__.loader is mod.__loader__
        assert mod.__file__
