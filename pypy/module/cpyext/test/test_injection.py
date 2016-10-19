from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestTypeObject(AppTestCpythonExtensionBase):

    def test_getitem_basic(self):
        module = self.import_module(name='injection')
        mything = module.test_mytype()
        assert mything[100] == 4200
        assert mything[-100] == -100+42

    def test_glob_make(self):
        module = self.import_module(name='injection')
        mything = module.make(5)
        assert mything is Ellipsis
        mything = module.make(15)
        assert mything[-100] == -100+15
