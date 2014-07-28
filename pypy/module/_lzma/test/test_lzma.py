class AppTestBZ2File:
    spaceconfig = {
        "usemodules": ["_lzma"]
    }

    def test_module(self):
        import lzma
