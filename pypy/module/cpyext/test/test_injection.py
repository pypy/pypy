from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestTypeObject(AppTestCpythonExtensionBase):

    def test_getitem_basic(self):
        module = self.import_module(name='injection')
        mything = module.test_mytype()
        assert mything[100] == 4200
