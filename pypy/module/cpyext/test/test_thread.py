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
#ifndef PyThread_get_thread_ident
#error "seems we are not accessing PyPy's functions"
#endif
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
#ifndef PyThread_allocate_lock
#error "seems we are not accessing PyPy's functions"
#endif
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
#ifndef PyThread_release_lock
#error "seems we are not accessing PyPy's functions"
#endif
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
#ifndef PyThread_acquire_lock_timed
#error "seems we are not accessing PyPy's functions"
#endif
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
                print("CCCC")
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
