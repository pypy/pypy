import py

import thread
import threading

from pypy.module.thread.ll_thread import allocate_ll_lock
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class TestPyThread(BaseApiTest):
    def test_get_thread_ident(self, space, api):
        results = []
        def some_thread():
            res = api.PyThread_get_thread_ident()
            results.append((res, thread.get_ident()))

        some_thread()
        assert results[0][0] == results[0][1]

        th = threading.Thread(target=some_thread, args=())
        th.start()
        th.join()
        assert results[1][0] == results[1][1]

        assert results[0][0] != results[1][0]

    def test_acquire_lock(self, space, api):
        assert hasattr(api, 'PyThread_acquire_lock')
        lock = api.PyThread_allocate_lock()
        assert api.PyThread_acquire_lock(lock, 1) == 1
        assert api.PyThread_acquire_lock(lock, 0) == 0
        api.PyThread_free_lock(lock)

    def test_release_lock(self, space, api):
        assert hasattr(api, 'PyThread_acquire_lock')
        lock = api.PyThread_allocate_lock()
        api.PyThread_acquire_lock(lock, 1)
        api.PyThread_release_lock(lock)
        assert api.PyThread_acquire_lock(lock, 0) == 1
        api.PyThread_free_lock(lock)


class AppTestThread(AppTestCpythonExtensionBase):
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
