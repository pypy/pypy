from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.genobject import PyGen_Check, PyGen_CheckExact
from pypy.module.cpyext.genobject import PyCoro_CheckExact


class TestGenObject(BaseApiTest):
    def test_genobject(self, space):
        w_geniter = space.appexec([], """():
            def f():
                yield 42
            return f()
        """)
        assert PyGen_Check(space, w_geniter)
        assert PyGen_CheckExact(space, w_geniter)
        assert not PyCoro_CheckExact(space, w_geniter)
        assert not PyGen_Check(space, space.wrap(2))
        assert not PyGen_CheckExact(space, space.wrap("b"))
        assert not PyCoro_CheckExact(space, space.wrap([]))

        w_coroutine = space.appexec([], """():
            async def f():
                pass
            return f()
        """)
        assert not PyGen_Check(space, w_coroutine)
        assert not PyGen_CheckExact(space, w_coroutine)
        assert PyCoro_CheckExact(space, w_coroutine)

class AppTestCoroutine(AppTestCpythonExtensionBase):
    def test_simple(self):
        """
        module = self.import_extension('test_coroutine', [
            ('await_', 'METH_O',
             '''
             PyAsyncMethods* am = args->ob_type->tp_as_async;
             if (am && am->am_await) {
                return am->am_await(args);
             }
             PyErr_SetString(PyExc_TypeError, "Not an awaitable");
             return NULL;
             '''),])
        async def f():
            pass
        raises(StopIteration, next, module.await_(f()))
        """
