import sys

import pytest

from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

only_pypy ="config.option.runappdirect and '__pypy__' not in sys.builtin_module_names"

class AppTestThread(AppTestCpythonExtensionBase):
    @pytest.mark.skipif(only_pypy, reason='pypy only test')
    @pytest.mark.xfail(reason='segfaults', run=False)
    def test_get_thread_ident(self):
        module = self.import_extension('foo', [
            ("get_thread_ident", "METH_NOARGS",
             """
                 return PyLong_FromLong(PyThread_get_thread_ident());
             """),
            ])
        import threading
        results = []
        def some_thread():
            res = module.get_thread_ident()
            results.append((res, threading.get_ident()))

        some_thread()
        assert results[0][0] == results[0][1]

        th = threading.Thread(target=some_thread, args=())
        th.start()
        th.join()
        assert results[1][0] == results[1][1]

        assert results[0][0] != results[1][0]

    @pytest.mark.skipif(only_pypy, reason='pypy only test')
    def test_acquire_lock(self):
        module = self.import_extension('foo', [
            ("test_acquire_lock", "METH_NOARGS",
             """
                 PyThread_type_lock lock = PyThread_allocate_lock();
                 if (PyThread_acquire_lock(lock, 1) != 1) {
                     PyErr_SetString(PyExc_AssertionError, "first acquire");
                     return NULL;
                 }
                 if (PyThread_acquire_lock(lock, 0) != 0) {
                     PyErr_SetString(PyExc_AssertionError, "second acquire");
                     return NULL;
                 }
                 PyThread_free_lock(lock);

                 Py_RETURN_NONE;
             """),
            ])
        module.test_acquire_lock()

    @pytest.mark.skipif(only_pypy, reason='pypy only test')
    def test_release_lock(self):
        module = self.import_extension('foo', [
            ("test_release_lock", "METH_NOARGS",
             """
                 PyThread_type_lock lock = PyThread_allocate_lock();
                 PyThread_acquire_lock(lock, 1);
                 PyThread_release_lock(lock);
                 if (PyThread_acquire_lock(lock, 0) != 1) {
                     PyErr_SetString(PyExc_AssertionError, "first acquire");
                     return NULL;
                 }
                 PyThread_free_lock(lock);

                 Py_RETURN_NONE;
             """),
            ])
        module.test_release_lock()

    @pytest.mark.skipif(only_pypy, reason='pypy only test')
    def test_timed_lock(self):
        module = self.import_extension('foo', [
            ("timed_acquire_lock", "METH_O",
             """
                PyLockStatus acquire_result;
                int microseconds = PyLong_AsLong(args);
                Py_BEGIN_ALLOW_THREADS
                acquire_result = PyThread_acquire_lock_timed(global_lock, microseconds, 0);
                Py_END_ALLOW_THREADS
                if (acquire_result == PY_LOCK_ACQUIRED) {
                    Py_RETURN_TRUE;
                } else {
                    Py_RETURN_FALSE;
                }
             """),
            ("release_lock", "METH_NOARGS",
              """
              PyThread_release_lock(global_lock);
              Py_RETURN_NONE;
              """),
            ("cleanup_lock", "METH_NOARGS",
              """
              // cleanup isn't part of the test, but I'd feel guilty otherwise
              PyThread_free_lock(global_lock); global_lock=NULL;
              Py_RETURN_NONE;
              """
             )
            ],
            prologue="static PyThread_type_lock global_lock;",
            more_init="global_lock = PyThread_allocate_lock();"
        )
        try:
            import threading
            import time
            failure = []
            assert module.timed_acquire_lock(-1)
            main_thread_should_release_the_lock_barrier = threading.Barrier(2)

            def thread_func():
                try:
                    if module.timed_acquire_lock(0):
                        failure.append("Lock should be held elsewhere")
                        return
                    if module.timed_acquire_lock(1):
                        failure.append("Lock should be held elsewhere")
                        return
                finally:
                    main_thread_should_release_the_lock_barrier.wait()
                if not module.timed_acquire_lock(1000000):
                    failure.append("Lock should have become available")
                    return
                module.release_lock()
            thread = threading.Thread(target=thread_func)
            thread.start()
            main_thread_should_release_the_lock_barrier.wait()
            # At this point, thread_func should be waiting 1s for the lock,
            # so sleep a short amount of time then let it have the lock.
            time.sleep(0.01)
            module.release_lock()

            thread.join()
            assert not failure, failure
        finally:
            module.cleanup_lock()

        # The intr_flag isn't tested here though

    @pytest.mark.skipif(only_pypy, reason='pypy only test')
    def test_poll_loop_in_c_yields_gil(self):
        # A C extension that polls Python state in a loop has to let other
        # threads run, otherwise the thread it is waiting for never gets to
        # set the flag it is polling for.  The equivalent loop written in
        # Python yields fine; only the C one starves.
        #
        # Cython compiles `while not done.is_set():` into exactly this shape,
        # which is why these Cython tests hang on PyPy (both listed in
        # Cython's tests/pypy_crash_bugs.txt):
        #     tests/run/generator_thread_safety.pyx
        #         test_value_into_generator, test_throw_into_generator
        #     tests/run/threadsafe_generated.pyx
        #         test_properties
        # Adding a sleep(0) to those loops makes all three pass, which is
        # what identifies this as the cause rather than a lock problem.
        #
        # Bounded by wall clock, so it reports starvation instead of hanging.
        #
        # NB: this PASSES untranslated -- the starvation only appears on a
        # translated build.  To see it fail, run the same loop against a
        # translated pypy:  ./pypy3.12-c pytest.py -D <this file>
        # A standalone C version starves after ~5.5M PyObject_CallMethod
        # calls in 4.85s without the setter thread running once, so this is
        # not specific to Cython-generated code.
        module = self.import_extension('foo', [
            ("poll_until_set", "METH_VARARGS",
             """
                PyObject *ev;
                int timeout;
                long i = 0;
                time_t deadline;
                if (!PyArg_ParseTuple(args, "Oi", &ev, &timeout))
                    return NULL;
                deadline = time(NULL) + timeout;
                while (time(NULL) < deadline) {
                    PyObject *res;
                    int is_set;
                    i++;
                    res = PyObject_CallMethod(ev, "is_set", NULL);
                    if (res == NULL)
                        return NULL;
                    is_set = PyObject_IsTrue(res);
                    Py_DECREF(res);
                    if (is_set < 0)
                        return NULL;
                    if (is_set)
                        return PyLong_FromLong(i);   /* saw it */
                }
                return PyLong_FromLong(-i);          /* starved */
             """),
            ],
            prologue="#include <time.h>")
        import threading, time

        ev = threading.Event()
        def setter():
            time.sleep(0.05)
            ev.set()
        t = threading.Thread(target=setter)
        t.start()
        # Untranslated, the loop runs fewer bytecodes in 5s than the
        # default check interval, so it would never yield the GIL at all.
        import sys
        old_interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-5)
        try:
            n = module.poll_until_set(ev, 5)
        finally:
            sys.setswitchinterval(old_interval)
        t.join(10)
        assert n > 0, (
            "C poll loop never saw the event: ran %d iterations over 5s "
            "while another thread was waiting to set it" % -n)

    @pytest.mark.skipif(only_pypy, reason='pypy only test')
    @pytest.mark.xfail(reason='segfaults', run=False)
    def test_tls(self):
        module = self.import_extension('foo', [
            ("create_key", "METH_NOARGS",
             """
                 return PyLong_FromLong(PyThread_create_key());
             """),
            ("test_key", "METH_O",
             """
                 int key = PyLong_AsLong(args);
                 if (PyThread_get_key_value(key) != NULL) {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 if (PyThread_set_key_value(key, (void*)123) < 0) {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 if (PyThread_get_key_value(key) != (void*)123) {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 Py_RETURN_NONE;
             """),
            ])
        key = module.create_key()
        assert key > 0
        # Test value in main thread.
        module.test_key(key)
        raises(ValueError, module.test_key, key)
        # Same test, in another thread.
        result = []
        import _thread, time
        def in_thread():
            try:
                module.test_key(key)
                raises(ValueError, module.test_key, key)
            except Exception as e:
                result.append(e)
            else:
                result.append(True)
        _thread.start_new_thread(in_thread, ())
        while not result:
            print(".")
            time.sleep(.5)
        assert result == [True]

    def test_tss(self):
        module = self.import_extension('foo', [
            ("tss", "METH_NOARGS",
             """
                void *tss_key = NULL;
                /* non-Py_LIMITED_API */
                Py_tss_t _tss_key = Py_tss_NEEDS_INIT;
                int the_value = 1;
                if ( PyThread_tss_is_created(&_tss_key) ) {
                     PyErr_SetString(PyExc_AssertionError,
                         "tss_is_created should not succeed yet");
                     return NULL;
                }
                /* This should be a no-op */
                PyThread_tss_delete(&_tss_key);
                /* Py_LIMITED_API */
                tss_key = PyThread_tss_alloc();
                if ( PyThread_tss_is_created(tss_key) ) {
                     PyErr_SetString(PyExc_AssertionError,
                         "tss_is_created should not succeed yet");
                     return NULL;
                }
                if (PyThread_tss_create(tss_key)) {
                    return NULL;
                }
                if (! PyThread_tss_is_created(tss_key)) {
                    return NULL;
                }
                /* Be sure additional calls succeed */
                if (PyThread_tss_create(tss_key)) {
                    return NULL;
                }
                if (PyThread_tss_get(tss_key) != NULL) {
                     PyErr_SetString(PyExc_AssertionError,
                         "tss_get should not succeed yet");
                    return NULL;
                }
                
                if (PyThread_tss_set(tss_key, (void *)&the_value)) {
                     PyErr_SetString(PyExc_AssertionError,
                         "tss_set failed");
                    return NULL;
                }
                void *val = PyThread_tss_get(tss_key);
                if (val == NULL) {
                     PyErr_SetString(PyExc_AssertionError,
                         "tss_get failed");
                    return NULL;
                }
                if (the_value != *(int*)val) {
                     PyErr_SetString(PyExc_AssertionError,
                         "retrieved value is wrong");
                    return NULL;
                }
                PyThread_tss_free(tss_key);
                Py_RETURN_NONE;
             """),
            ])
        module.tss()
