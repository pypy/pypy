from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestTypeObject(AppTestCpythonExtensionBase):
    def test_module_exists(self):
        module = self.import_module(name='injection')
