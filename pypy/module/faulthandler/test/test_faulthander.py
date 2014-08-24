class AppTestFaultHandler:
    spaceconfig = {
        "usemodules": ["faulthandler"]
    }

    def test_enable(self):
        import faulthandler
        faulthandler.enable()
        assert faulthandler.is_enabled() is True
        faulthandler.disable()
        assert faulthandler.is_enabled() is False

    def test_dump_traceback(self):
        import faulthandler
        faulthandler.dump_traceback()
        
