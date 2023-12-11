from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestSignature(AppTestCpythonExtensionBase):
    def test_import(self):
        module = self.import_module(name='signature')

    def test_call_inc(self):
        module = self.import_module(name='signature')
        result = module.inc(4)
        assert result == 5
