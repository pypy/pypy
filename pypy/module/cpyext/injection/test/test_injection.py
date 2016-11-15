from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.pyobject import _has_a_pyobj
from pypy.interpreter.gateway import interp2app
from pypy.conftest import option

class AppTestTypeObject(AppTestCpythonExtensionBase):

    def setup_class(cls):
        if option.runappdirect:
            skip('untranslated only')
        def is_there_an_pyobj_version(space, w_obj):
            if _has_a_pyobj(space, w_obj):
                return space.w_True
            return space.w_False
        cls.w_is_there_an_pyobj_version = cls.space.wrap(
                         interp2app(is_there_an_pyobj_version))
        AppTestCpythonExtensionBase.setup_class.im_func(cls)

    def test_getitem_basic(self):
        module = self.import_module(name='injection', filename='../injection/test/injection')
        mything = module.test_mytype()
        assert mything[100] == 4200
        assert mything[-100] == -100+42

    def test_glob_make(self):
        module = self.import_module(name='injection', filename='../injection/test/injection')
        mything = module.make(5)
        assert mything is Ellipsis
        mything = module.make(15)
        assert mything[-100] == -100+15

    def test_pypy_only_version_of_object(self):
        module = self.import_module(name='injection', filename='../injection/test/injection')
        mything = module.make(25)
        assert not self.is_there_an_pyobj_version(mything)
        assert mything[100] == 25*100
        assert not self.is_there_an_pyobj_version(mything)
        assert mything[-100] == -100+25
        assert self.is_there_an_pyobj_version(mything)

