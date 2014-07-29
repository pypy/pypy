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
