from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem.lltype import nullptr
from pypy.module.cpyext.pystate import PyInterpreterState, PyThreadState
from pypy.module.cpyext.pyobject import from_ref

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

class TestInterpreterState(BaseApiTest):
    def test_interpreter_head(self, space, api):
        state = api.PyInterpreterState_Head()
        assert state != nullptr(PyInterpreterState.TO)

    def test_interpreter_next(self, space, api):
        state = api.PyInterpreterState_Head()
        assert nullptr(PyInterpreterState.TO) == api.PyInterpreterState_Next(state)

class TestThreadState(BaseApiTest):
    def test_thread_state_get(self, space, api):
        ts = api.PyThreadState_Get()
        assert ts != nullptr(PyThreadState.TO)

    def test_thread_state_interp(self, space, api):
        ts = api.PyThreadState_Get()
        assert ts.c_interp == api.PyInterpreterState_Head()
        assert ts.c_interp.c_next == nullptr(PyInterpreterState.TO)

    def test_basic_threadstate_dance(self, space, api):
        # Let extension modules call these functions,
        # Not sure of the semantics in pypy though.
        # (cpyext always acquires and releases the GIL around calls)
        tstate = api.PyThreadState_Swap(None)
        assert tstate is not None
        assert not api.PyThreadState_Swap(tstate)

        api.PyEval_AcquireThread(tstate)
        api.PyEval_ReleaseThread(tstate)

    def test_threadstate_dict(self, space, api):
        ts = api.PyThreadState_Get()
        ref = ts.c_dict
        assert ref == api.PyThreadState_GetDict()
        w_obj = from_ref(space, ref)
        assert space.isinstance_w(w_obj, space.w_dict)

    def test_savethread(self, space, api):
        thread = api.PyImport_Import(space.wrap("thread"))
        space.threadlocals.setup_threads(space)

        ts = api.PyEval_SaveThread()
        assert ts
        assert api.PyThreadState_Get() == nullptr(PyThreadState.TO)
        api.PyEval_RestoreThread(ts)
        assert api.PyThreadState_Get() != nullptr(PyThreadState.TO)
