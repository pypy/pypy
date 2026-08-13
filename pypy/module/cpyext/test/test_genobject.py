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

class AppTestCythonGenerator(AppTestCpythonExtensionBase):
    def test_any_in_conditional_gen(self):
        # Reproduces a crash seen running the Cython test suite: a
        # Cython-compiled generator expression that any() abandons
        # mid-iteration (short-circuit) gets garbage collected while
        # suspended.  Its tp_dealloc calls PyObject_ClearWeakRefs(self)
        # unconditionally (CPython 3.12+ codegen), which used to crash
        # cpyext's "dying object" reentrancy guard even though the
        # object never had any weakrefs.
        mod = self.import_module(name="any")
        assert mod.any_in_conditional_gen([3, 6, 9]) is False
        assert mod.any_in_conditional_gen([0, 3, 7]) is True
        self.debug_collect()


class AppTestCoroutine(AppTestCpythonExtensionBase):
    def test_generator_coroutine(self):
        module = self.import_extension('test_gen', [
            ('is_coroutine', 'METH_O',
             '''
             if (!PyGen_CheckExact(args))
                Py_RETURN_NONE;
             PyObject* co = ((PyGenObject*)args)->gi_code;
             if (((PyCodeObject*)co)->co_flags & CO_ITERABLE_COROUTINE)
                Py_RETURN_TRUE;
             else
                Py_RETURN_FALSE;
             ''')])

        def it():
            yield 42

        assert module.is_coroutine(it()) is False
        self.debug_collect()  # don't crash while deallocating
        from types import coroutine
        assert module.is_coroutine(coroutine(it)()) is True

    def test_await(self):
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
