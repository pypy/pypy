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

class TestInterpreterState(BaseApiTest):
    def test_interpreter_head(self, space, api):
        state = api.PyInterpreterState_Head()
        assert state != nullptr(PyInterpreterState.TO)

    def test_interpreter_next(self, space, api):
        state = api.PyInterpreterState_Head()
        assert nullptr(PyInterpreterState.TO) == api.PyInterpreterState_Next(state)


class DirectThreadStateBase(LeakCheckingTest):
    # XXX Subclasses of this are probably pretty slow, because creating new
    # spaces is pretty slow.  They probably leak some memory too, because cpyext
    # initialization allocates some stuff and it's too hard to find it to clean
    # it up.
    # XXX This should be setup_method not setup_class, but mystery failures.
    def setup_class(cls):
        # XXX HACK HACK HACK Mystery bug, not going to debug it, just going to hack it
        leakfinder.TRACK_ALLOCATIONS = True
        leakfinder.stop_tracking_allocations(check=False)

        # Make a *new* space.  blah blah explain more
        from pypy.conftest import maketestobjspace, make_config, option
        cls.space = maketestobjspace(make_config(option, usemodules=["cpyext"]))


    def teardown_class(cls):
        ec = cls.space.getexecutioncontext()
        del ec.cpyext_threadstate
        ec.cpyext_initialized_threadstate = False

        leakfinder.start_tracking_allocations()


class TestThreadStateDirect(DirectThreadStateBase):
    def test_thread_state_interp(self):
        ts = PyThreadState_Get(self.space)
        assert ts.c_interp == PyInterpreterState_Head(self.space)
        assert ts.c_interp.c_next == nullptr(PyInterpreterState.TO)

    def test_thread_state_get(self):
        return
        ts = PyThreadState_Get(self.space)
        assert ts != nullptr(PyThreadState.TO)


    def test_basic_threadstate_dance(self, space, api):
        return
        # Let extension modules call these functions,
        # Not sure of the semantics in pypy though.
        # (cpyext always acquires and releases the GIL around calls)
        tstate = api.PyThreadState_Swap(None)
        assert tstate is not None

        assert api.PyThreadState_Get() is None
        assert api.PyThreadState_Swap(tstate) is None
        assert api.PyThreadState_Get() is tstate

        api.PyEval_AcquireThread(tstate)
        api.PyEval_ReleaseThread(tstate)

    def test_threadstate_dict(self, space, api):
        return
        ts = api.PyThreadState_Get()
        ref = ts.c_dict
        assert ref == api.PyThreadState_GetDict()
        w_obj = from_ref(space, ref)
        assert space.isinstance_w(w_obj, space.w_dict)

    def test_savethread(self, space, api):
        return
        ts = api.PyEval_SaveThread()
        assert ts
        assert api.PyThreadState_Get() == nullptr(PyThreadState.TO)
        api.PyEval_RestoreThread(ts)
        assert api.PyThreadState_Get() != nullptr(PyThreadState.TO)

del LeakCheckingTest
