
class AppTestMagic:
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_save_module_content_for_future_reload(self):
        import sys, __pypy__
        d = sys.dont_write_bytecode
        sys.dont_write_bytecode = "hello world"
        __pypy__.save_module_content_for_future_reload(sys)
        sys.dont_write_bytecode = d
        reload(sys)
        assert sys.dont_write_bytecode == "hello world"
        #
        sys.dont_write_bytecode = d
        __pypy__.save_module_content_for_future_reload(sys)
