from .support import HPyTest

class AppTestBasic(HPyTest):
    spaceconfig = {'usemodules': ['hpy_universal']}
    def test_import(self):
        import hpy_universal

    def test_empty_module(self):
        import sys
        mod = self.make_module("""
            @INIT
        """)
        assert type(mod) is type(sys)
        assert mod.__loader__.name == 'mytest'
        assert mod.__spec__.loader is mod.__loader__
        assert mod.__file__

