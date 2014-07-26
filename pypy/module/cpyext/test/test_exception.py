from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.pyobject import make_ref

class TestExceptions(BaseApiTest):

    def test_ExceptionInstance_Class(self, space, api):
        w_instance = space.call_function(space.w_ValueError)
        assert api.PyExceptionInstance_Class(w_instance) is space.w_ValueError

    def test_traceback(self, space, api):
        w_exc = space.call_function(space.w_ValueError)
        assert api.PyException_GetTraceback(w_exc) is None
        assert api.PyException_SetTraceback(w_exc, space.wrap(1)) == -1
        api.PyErr_Clear()

    def test_context(self, space, api):
        w_exc = space.call_function(space.w_ValueError)
        assert api.PyException_GetContext(w_exc) is None
        w_ctx = space.call_function(space.w_IndexError)
        api.PyException_SetContext(w_exc, make_ref(space, w_ctx))
        assert space.is_w(api.PyException_GetContext(w_exc), w_ctx)

    def test_cause(self, space, api):
        w_exc = space.call_function(space.w_ValueError)
        assert api.PyException_GetCause(w_exc) is None
        w_cause = space.call_function(space.w_IndexError)
        api.PyException_SetCause(w_exc, make_ref(space, w_cause))
        assert space.is_w(api.PyException_GetCause(w_exc), w_cause)


class AppTestExceptions(AppTestCpythonExtensionBase):

    def test_OSError_aliases(self):
        module = self.import_extension('foo', [
            ("get_aliases", "METH_NOARGS",
             """
                 return PyTuple_Pack(2,
                                     PyExc_EnvironmentError,
                                     PyExc_IOError);
             """),
            ])
        assert module.get_aliases() == (OSError, OSError)
