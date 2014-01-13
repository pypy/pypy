import py

from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestThread(AppTestCpythonExtensionBase):
    def test_get_thread_ident(self):
        module = self.import_extension('foo', [
            ("get_thread_ident", "METH_NOARGS",
             """
#ifndef PyThread_get_thread_ident
#error "seems we are not accessing PyPy's functions"
#endif
                 return PyInt_FromLong(PyThread_get_thread_ident());
             """),
            ])
        import thread, threading
        results = []
        def some_thread():
            res = module.get_thread_ident()
            results.append((res, thread.get_ident()))

        some_thread()
        assert results[0][0] == results[0][1]

        th = threading.Thread(target=some_thread, args=())
        th.start()
        th.join()
        assert results[1][0] == results[1][1]

        assert results[0][0] != results[1][0]

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

    def test_tls(self):
        module = self.import_extension('foo', [
            ("create_key", "METH_NOARGS",
             """
                 return PyInt_FromLong(PyThread_create_key());
             """),
            ("test_key", "METH_O",
             """
                 int key = PyInt_AsLong(args);
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
        import thread, time
        def in_thread():
            try:
                module.test_key(key)
                raises(ValueError, module.test_key, key)
            except Exception, e:
                result.append(e)
            else:
                result.append(True)
        thread.start_new_thread(in_thread, ())
        while not result:
            print "."
            time.sleep(.5)
        assert result == [True]
