import py, pytest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem.lltype import nullptr
from pypy.module.cpyext.pystate import PyInterpreterState, PyThreadState
from pypy.module.cpyext.pyobject import from_ref
from rpython.rtyper.lltypesystem import lltype
from pypy.module.cpyext.test.test_cpyext import LeakCheckingTest, freeze_refcnts
from pypy.module.cpyext.pystate import PyThreadState_Get, PyInterpreterState_Head
from rpython.tool import leakfinder

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

    def test_gilstate(self):
        module = self.import_extension('foo', [
            ("double_ensure", "METH_O",
             '''
                PyGILState_STATE state0, state1;
                int val = PyLong_AsLong(args);
                PyEval_InitThreads();
                state0 = PyGILState_Ensure(); /* hangs here */
                if (val != 0)
                {
                    state1 = PyGILState_Ensure();
                    PyGILState_Release(state1);
                }
                PyGILState_Release(state0);
                Py_RETURN_NONE;
             '''),
            ])
        module.double_ensure(0)
        print '0 ok'
        module.double_ensure(1)
        print '1 ok'


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
                     PyObject *d;

                     PyEval_InitThreads();

                     old_tstate = PyThreadState_Swap(NULL);
                     if (old_tstate == NULL) {
                         return PyLong_FromLong(0);
                     }

                     d = PyThreadState_GetDict(); /* fails on cpython */
                     if (d != NULL) {
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
                 PyThreadState * tstate;
                 if (PyEval_ThreadsInitialized() == 0)
                 {
                    PyEval_InitThreads();
                 }
                 PyGILState_Ensure();
                 tstate = PyEval_SaveThread();
                 if (tstate == NULL) {
                     return PyLong_FromLong(0);
                 }

                 PyEval_RestoreThread(tstate);

                 if (PyThreadState_Get() != tstate) {
                     return PyLong_FromLong(1);
                 }

                 return PyLong_FromLong(3);
                                  """),
                ])
        res = module.bounce()
        assert res == 3

    def test_thread_and_gil(self):
        module = self.import_extension('foo', [
            ("bounce", "METH_NOARGS",
            """
            PyThreadState * tstate;
            PyObject *dict;
            PyGILState_STATE gilstate;

            if (PyEval_ThreadsInitialized() == 0)
            {
            PyEval_InitThreads();
            }
            tstate = PyEval_SaveThread();
            if (tstate == NULL) {
                return PyLong_FromLong(0);
            }
            if (PyGILState_Check() != 0)
                return PyLong_FromLong(-1);
            dict = PyThreadState_GetDict();
            if (dict != NULL) {
            return PyLong_FromLong(1);
            }
            gilstate = PyGILState_Ensure();
            dict = PyThreadState_GetDict();
            if (dict == NULL) {
            return PyLong_FromLong(2);
            }
            if (PyGILState_Check() != 1)
                return PyLong_FromLong(-2);
            PyGILState_Release(gilstate);
            if (PyGILState_Check() != 0)
                return PyLong_FromLong(-3);
            PyEval_RestoreThread(tstate);

            if (PyThreadState_Get() != tstate) {
                return PyLong_FromLong(3);
            }
            if (PyGILState_Check() != 1)
                return PyLong_FromLong(-4);

            return PyLong_FromLong(4);
            """)])
        res = module.bounce()
        assert res == 4

    def test_nested_pygilstate_ensure(self):
        module = self.import_extension('foo', [
            ("bounce", "METH_NOARGS",
            """
            PyGILState_STATE gilstate;
            PyObject *dict;

            if (PyEval_ThreadsInitialized() == 0)
                PyEval_InitThreads();
            dict = PyThreadState_GetDict();
            gilstate = PyGILState_Ensure();
            PyGILState_Release(gilstate);
            if (PyThreadState_GetDict() != dict)
                return PyLong_FromLong(-2);
            return PyLong_FromLong(4);
            """)])
        res = module.bounce()
        assert res == 4

    def test_threadsinitialized(self):
        module = self.import_extension('foo', [
                ("test", "METH_NOARGS",
                 """
                 return PyInt_FromLong(PyEval_ThreadsInitialized());
                 """),
                ])
        res = module.test()
        print "got", res
        assert res in (0, 1)

    def test_thread_interrupt(self):
        import signal # to initialize the signal infrastructure
        import thread, time, posix as os

        module = self.import_extension('disruptor', [
                ("surprise", "METH_VARARGS",
                 """
                 long tid;
                 PyObject *exc;
                 if (!PyArg_ParseTuple(args, "lO", &tid, &exc))
                     return NULL;
                 return PyInt_FromLong(PyThreadState_SetAsyncExc(tid, exc));
                 """),
                ("nosurprise", "METH_VARARGS",
                 """
                 long tid;
                 if (!PyArg_ParseTuple(args, "l", &tid))
                     return NULL;
                 return PyInt_FromLong(PyThreadState_SetAsyncExc(tid, NULL));
                 """),
                ])
        # raise in another thread
        def f():
            try:
                childstarted.append(thread.get_ident())
                while 1:
                    print "waiting in child"
                    time.sleep(0.1)
            except KeyError:
                childstarted.pop()
            else:
                thread.interrupt_main() # to crash the test
        cancelled_exception = False

        for i in range(20):
            print i
            # first wait for the child to start
            childstarted = []
            thread.start_new_thread(f, ())
            for i in range(500):
                if childstarted:
                    break
                time.sleep(0.1)
            # then interrupt it from the main thread
            res = module.surprise(childstarted[0], KeyError)
            assert res == 1

            # try to cancel the interrupt
            # this is racing! the child could either have been terminated
            # already or not
            try:
                res = module.nosurprise(childstarted[0])
                assert res in (0, 1)
            except IndexError:
                pass
            else:
                if res == 1:
                    cancelled_exception = True
                    # actually send exception
                    res = module.surprise(childstarted[0], KeyError)
                    assert res in (0, 1)
            # now wait for the exception to arrive in the child thread
            # which empties childstarted again
            for i in range(500):
                if not childstarted:
                    break
                time.sleep(0.1)
            assert res == 1
        assert cancelled_exception # XXX I have no clue whether we can expect this to work or not

        # raise to main
        with raises(ValueError):
            res = module.surprise(thread.get_ident(), ValueError)
            while 1:
                print "sleeping"
                time.sleep(0.1)




class AppTestState(AppTestCpythonExtensionBase):

    def test_frame_tstate_tracing(self):
        import sys, threading
        module = self.import_extension('foo', [
            ("call_in_temporary_c_thread", "METH_O",
             """
                PyObject *res = NULL;
                test_c_thread_t test_c_thread;
                long thread;

                PyEval_InitThreads();

                test_c_thread.start_event = PyThread_allocate_lock();
                test_c_thread.exit_event = PyThread_allocate_lock();
                test_c_thread.callback = NULL;
                if (!test_c_thread.start_event || !test_c_thread.exit_event) {
                    PyErr_SetString(PyExc_RuntimeError, "could not allocate lock");
                    goto exit;
                }

                Py_INCREF(args);
                test_c_thread.callback = args;

                PyThread_acquire_lock(test_c_thread.start_event, 1);
                PyThread_acquire_lock(test_c_thread.exit_event, 1);

                thread = PyThread_start_new_thread(temporary_c_thread, &test_c_thread);
                if (thread == -1) {
                    PyErr_SetString(PyExc_RuntimeError, "unable to start the thread");
                    PyThread_release_lock(test_c_thread.start_event);
                    PyThread_release_lock(test_c_thread.exit_event);
                    goto exit;
                }

                PyThread_acquire_lock(test_c_thread.start_event, 1);
                PyThread_release_lock(test_c_thread.start_event);

                Py_BEGIN_ALLOW_THREADS
                    PyThread_acquire_lock(test_c_thread.exit_event, 1);
                    PyThread_release_lock(test_c_thread.exit_event);
                Py_END_ALLOW_THREADS

                Py_INCREF(Py_None);
                res = Py_None;

            exit:
                Py_CLEAR(test_c_thread.callback);
                if (test_c_thread.start_event)
                    PyThread_free_lock(test_c_thread.start_event);
                if (test_c_thread.exit_event)
                    PyThread_free_lock(test_c_thread.exit_event);
                return res;
            """), ], prologue = """
            #include "pythread.h"
            typedef struct {
                PyThread_type_lock start_event;
                PyThread_type_lock exit_event;
                PyObject *callback;
            } test_c_thread_t;

            static void
            temporary_c_thread(void *data)
            {
                test_c_thread_t *test_c_thread = data;
                PyGILState_STATE state;
                PyObject *res;

                PyThread_release_lock(test_c_thread->start_event);

                /* Allocate a Python thread state for this thread */
                state = PyGILState_Ensure();

                res = PyObject_CallFunction(test_c_thread->callback, "", NULL);
                Py_CLEAR(test_c_thread->callback);

                if (res == NULL) {
                    PyErr_Print();
                }
                else {
                    Py_DECREF(res);
                }

                /* Destroy the Python thread state for this thread */
                PyGILState_Release(state);

                PyThread_release_lock(test_c_thread->exit_event);

                /*PyThread_exit_thread(); NOP (on linux) and not implememnted */
            };
            """)
        def noop_trace(frame, event, arg):
            # no operation
            return noop_trace

        def generator():
            while 1:
                yield "genereator"

        def callback():
            if callback.gen is None:
                callback.gen = generator()
            return next(callback.gen)
        callback.gen = None

        old_trace = sys.gettrace()
        sys.settrace(noop_trace)
        try:
            # Install a trace function
            threading.settrace(noop_trace)

            # Create a generator in a C thread which exits after the call
            module.call_in_temporary_c_thread(callback)

            # Call the generator in a different Python thread, check that the
            # generator didn't keep a reference to the destroyed thread state
            for test in range(3):
                # The trace function is still called here
                callback()
        finally:
            sys.settrace(old_trace)


class TestInterpreterState(BaseApiTest):
    def test_interpreter_head(self, space, api):
        state = api.PyInterpreterState_Head()
        assert state != nullptr(PyInterpreterState.TO)

    def test_interpreter_next(self, space, api):
        state = api.PyInterpreterState_Head()
        assert nullptr(PyInterpreterState.TO) == api.PyInterpreterState_Next(state)
