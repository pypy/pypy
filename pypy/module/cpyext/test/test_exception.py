from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.pyobject import make_ref
from pypy.module.cpyext.exception import (
    PyExceptionInstance_Class, PyException_GetTraceback,
    PyException_SetTraceback, PyException_GetContext, PyException_SetContext,
    PyException_GetCause, PyException_SetCause,
    PyException_GetArgs, PyException_SetArgs)

class TestExceptions(BaseApiTest):

    def test_ExceptionInstance_Class(self, space):
        w_instance = space.call_function(space.w_ValueError)
        assert PyExceptionInstance_Class(
            space, w_instance) is space.w_ValueError

    def test_traceback(self, space):
        w_exc = space.call_function(space.w_ValueError)
        assert PyException_GetTraceback(space, w_exc) is None
        with raises_w(space, TypeError):
            PyException_SetTraceback(space, w_exc, space.wrap(1))

    def test_context(self, space):
        w_exc = space.call_function(space.w_ValueError)
        assert PyException_GetContext(space, w_exc) is None
        w_ctx = space.call_function(space.w_IndexError)
        PyException_SetContext(space, w_exc, make_ref(space, w_ctx))
        assert space.is_w(PyException_GetContext(space, w_exc), w_ctx)

    def test_cause(self, space):
        w_exc = space.call_function(space.w_ValueError)
        assert PyException_GetCause(space, w_exc) is None
        w_cause = space.call_function(space.w_IndexError)
        PyException_SetCause(space, w_exc, make_ref(space, w_cause))
        assert space.is_w(PyException_GetCause(space, w_exc), w_cause)

    def test_args(self, space):
        w_exc = space.call_function(space.w_ValueError, space.wrap(1))
        w_args = PyException_GetArgs(space, w_exc)
        assert space.eq_w(w_args, space.newtuple([space.wrap(1)]))
        w_newargs = space.newtuple([space.wrap(2), space.wrap(3)])
        PyException_SetArgs(space, w_exc, w_newargs)
        assert space.eq_w(PyException_GetArgs(space, w_exc), w_newargs)


class AppTestExceptions(AppTestCpythonExtensionBase):

    def test_OSError_aliases(self):
        module = self.import_extension('foo', [
            ("get_aliases", "METH_NOARGS",
             """
                 return PyTuple_Pack(2,
                                     PyExc_EnvironmentError,
                                     PyExc_IOError);
             """)])
        assert module.get_aliases() == (OSError, OSError)

    def test_implicit_chaining(self):
        module = self.import_extension('foo', [
            ("raise_exc", "METH_NOARGS",
             """
                PyObject *ev, *et, *tb;
                PyObject *ev0, *et0, *tb0;
                PyErr_GetExcInfo(&ev0, &et0, &tb0);
                PyErr_SetString(PyExc_ValueError, "foo");

                // simplified copy of __Pyx_GetException
                PyErr_Fetch(&et, &ev, &tb);
                PyErr_NormalizeException(&et, &ev, &tb);
                if (tb) PyException_SetTraceback(ev, tb);
                PyErr_SetExcInfo(et, ev, tb);

                PyErr_SetString(PyExc_TypeError, "bar");
                PyErr_SetExcInfo(ev0, et0, tb0);
                return NULL;
             """)])
        excinfo = raises(TypeError, module.raise_exc)
        assert excinfo.value.__context__

    def test_heaptype_dealloc_calls_base_tp_dealloc(self):
        # Regression test for issue 5555: a heap type deriving from a
        # builtin exception, whose own tp_dealloc follows the documented
        # CPython convention (call the base's tp_dealloc, then decref its
        # own type if the base is not itself a heap type).
        module = self.import_extension('foo_5555', [
            ("get_type", "METH_NOARGS", """
                PyObject *bases = PyTuple_Pack(1, PyExc_Exception);
                if (bases == NULL) return NULL;
                PyObject *type = PyType_FromSpecWithBases(&Repro_spec, bases);
                Py_DECREF(bases);
                return type;
             """),
            ("get_refcnt", "METH_O", """
                return PyLong_FromSsize_t(Py_REFCNT(args));
             """)],
            prologue="""
            typedef struct {
                PyObject ob_base;
            } ReproObject;

            static PyObject *
            Repro_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
            {
                PyObject *empty_args = PyTuple_New(0);
                if (empty_args == NULL) return NULL;
                PyTypeObject *base = (PyTypeObject *)PyExc_Exception;
                PyObject *obj = base->tp_new(type, empty_args, NULL);
                Py_DECREF(empty_args);
                return obj;
            }

            static void
            Repro_dealloc(PyObject *self)
            {
                PyTypeObject *type = Py_TYPE(self);
                PyTypeObject *base = (PyTypeObject *)PyExc_Exception;
                int type_needs_decref = (
                    PyType_HasFeature(type, Py_TPFLAGS_HEAPTYPE) &&
                    !PyType_HasFeature(base, Py_TPFLAGS_HEAPTYPE));
                base->tp_dealloc(self);
                if (type_needs_decref) {
                    Py_DECREF(type);
                }
            }

            static PyType_Slot Repro_slots[] = {
                {Py_tp_dealloc, Repro_dealloc},
                {Py_tp_new, Repro_new},
                {0, 0}
            };

            static PyType_Spec Repro_spec = {
                "foo_5555.Repro",
                sizeof(ReproObject),
                0,
                Py_TPFLAGS_DEFAULT,
                Repro_slots
            };
            """)
        Repro = module.get_type()
        assert issubclass(Repro, Exception)
        refcount_before = module.get_refcnt(Repro)
        for _ in range(5):
            exc = Repro()
            del exc
            for i in range(10):
                if module.get_refcnt(Repro) <= refcount_before:
                    break
                self.debug_collect()
            assert module.get_refcnt(Repro) == refcount_before

