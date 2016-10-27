from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.pyobject import _has_a_pyobj
from pypy.interpreter.gateway import interp2app

class AppTestTypeObject(AppTestCpythonExtensionBase):

    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)

    def test_float64(self):
        np = self.import_module(name='numpy.core.multiarray',
                                filename='../injection/test/multiarray')
        assert type(np.typeinfo['DOUBLE'][-1]) is type

    def test_plain_getitem(self):
        np = self.import_module(name='numpy.core.multiarray_PLAIN',
                                filename='../injection/test/multiarray')
        array = np.ndarray(100)
        array[10] = 1.0
        assert array[10] == 1.0 + 42    # hacked
        float64 = np.typeinfo['DOUBLE'][-1]
        assert type(array[10]) is float64

    def test_injected_getitem(self):
        np = self.import_module(name='numpy.core.multiarray',
                                filename='../injection/test/multiarray')
        array = np.ndarray(100)
        array[10] = 1.0
        assert array[10] == 1.0
        assert array[10] + array[10] == 2.0
        float64 = np.typeinfo['DOUBLE'][-1]
        assert type(array[10]) is float64
        class X(np.ndarray):
            pass

        x = X(1)
        assert isinstance(x, X)
        assert isinstance(x, np.ndarray)

    def test_plain_op(self):
        np = self.import_module(name='numpy.core.multiarray_PLAIN',
                                filename='../injection/test/multiarray')
        a = np.ndarray(100);
        for i in range(100):
            a[i] = i
        b = a * a
        assert b[10] == 100.0 + 42.0

    def test_injected_op(self):
        np = self.import_module(name='numpy.core.multiarray',
                                filename='../injection/test/multiarray')
        a = np.ndarray(100);
        for i in range(100):
            a[i] = i
        b = a * a
        assert b[10] == 100.0
