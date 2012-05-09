from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem.lltype import nullptr
from pypy.module.cpyext.pystate import PyInterpreterState, PyThreadState
from pypy.module.cpyext.pyobject import from_ref
from pypy.rpython.lltypesystem import lltype
from pypy.module.cpyext.test.test_cpyext import LeakCheckingTest, freeze_refcnts
from pypy.module.cpyext.pystate import PyThreadState_Get, PyInterpreterState_Head
from pypy.tool import leakfinder

class AppTestThreads(AppTestCpythonExtensionBase):
    def test_allow_threads(self):
        module = self.import_extension('foo', [
            ("test", "METH_NOARGS",
             """
                Py_BEGIN_ALLOW_THREADS
                {
                    Py_BLOCK_THREADS
                    Py_UNBLOCK_THREADS
                }
                Py_END_ALLOW_THREADS
                Py_RETURN_NONE;
             """),
            ])
        # Should compile at least
        module.test()


    def test_thread_state_get(self):
        module = self.import_extension('foo', [
                ("get", "METH_NOARGS",
                 """
                     PyThreadState *tstate = PyThreadState_Get();
                     if (tstate == NULL) {
                         return PyLong_FromLong(0);
                     }
                     if (tstate->interp != PyInterpreterState_Head()) {
                         return PyLong_FromLong(1);
                     }
                     if (tstate->interp->next != NULL) {
                         return PyLong_FromLong(2);
                     }
                     return PyLong_FromLong(3);
                 """),
                ])
        assert module.get() == 3

    def test_basic_threadstate_dance(self):
        module = self.import_extension('foo', [
                ("dance", "METH_NOARGS",
                 """
                     PyThreadState *old_tstate, *new_tstate;

                     old_tstate = PyThreadState_Swap(NULL);
                     if (old_tstate == NULL) {
                         return PyLong_FromLong(0);
                     }

                     new_tstate = PyThreadState_Get();
                     if (new_tstate != NULL) {
                         return PyLong_FromLong(1);
                     }

                     new_tstate = PyThreadState_Swap(old_tstate);
                     if (new_tstate != NULL) {
                         return PyLong_FromLong(2);
                     }

                     new_tstate = PyThreadState_Get();
                     if (new_tstate != old_tstate) {
                         return PyLong_FromLong(3);
                     }

                     return PyLong_FromLong(4);
                 """),
                ])
        assert module.dance() == 4

    def test_threadstate_dict(self):
        module = self.import_extension('foo', [
                ("getdict", "METH_NOARGS",
                 """
                 PyObject *dict = PyThreadState_GetDict();
                 Py_INCREF(dict);
                 return dict;
                 """),
                ])
        assert isinstance(module.getdict(), dict)

    def test_savethread(self):
        module = self.import_extension('foo', [
                ("bounce", "METH_NOARGS",
                 """
                 PyThreadState *tstate = PyEval_SaveThread();
                 if (tstate == NULL) {
                     return PyLong_FromLong(0);
                 }

                 if (PyThreadState_Get() != NULL) {
                     return PyLong_FromLong(1);
                 }

                 PyEval_RestoreThread(tstate);

                 if (PyThreadState_Get() != tstate) {
                     return PyLong_FromLong(2);
                 }

                 return PyLong_FromLong(3);
                                  """),
                ])



class TestInterpreterState(BaseApiTest):
    def test_interpreter_head(self, space, api):
        state = api.PyInterpreterState_Head()
        assert state != nullptr(PyInterpreterState.TO)

    def test_interpreter_next(self, space, api):
        state = api.PyInterpreterState_Head()
        assert nullptr(PyInterpreterState.TO) == api.PyInterpreterState_Next(state)
