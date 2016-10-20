from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.pyobject import _has_a_pyobj
from pypy.interpreter.gateway import interp2app

class AppTestTypeObject(AppTestCpythonExtensionBase):

    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)

    def test_getitem_basic(self):
        np = self.import_module(name='multiarray', filename='../injection/test/multiarray')
        array = np.ndarray(100)
        array[10] = 1.0
        assert array[10] == 1.0
