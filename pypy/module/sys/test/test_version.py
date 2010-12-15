class AppTestVersion:
    def test_compiler(self):
        import sys
        assert ("MSC v." in sys.version or
                "GCC " in sys.version)
