import pytest
import sys
import StringIO

from pypy.module.cpyext.state import State
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi, ll2ctypes

from pypy.interpreter.gateway import interp2app

class TestExceptions(BaseApiTest):
    def test_GivenExceptionMatches(self, space, api):
        exc_matches = api.PyErr_GivenExceptionMatches

        string_exception = space.wrap('exception')
        instance = space.call_function(space.w_ValueError)
        assert exc_matches(string_exception, string_exception)
        assert exc_matches(instance, space.w_ValueError)
        assert exc_matches(space.w_ValueError, space.w_ValueError)
        assert exc_matches(space.w_IndexError, space.w_LookupError)
        assert not exc_matches(space.w_ValueError, space.w_LookupError)

        exceptions = space.newtuple([space.w_LookupError, space.w_ValueError])
        assert exc_matches(space.w_ValueError, exceptions)

    def test_ExceptionMatches(self, space, api):
        api.PyErr_SetObject(space.w_ValueError, space.wrap("message"))
        assert api.PyErr_ExceptionMatches(space.w_Exception)
        assert api.PyErr_ExceptionMatches(space.w_ValueError)
        assert not api.PyErr_ExceptionMatches(space.w_TypeError)

        api.PyErr_Clear()

    def test_Occurred(self, space, api):
        assert not api.PyErr_Occurred()
        string = rffi.str2charp("spam and eggs")
        api.PyErr_SetString(space.w_ValueError, string)
        rffi.free_charp(string)
        assert api.PyErr_Occurred() is space.w_ValueError

        api.PyErr_Clear()

    def test_SetObject(self, space, api):
        api.PyErr_SetObject(space.w_ValueError, space.wrap("a value"))
        assert api.PyErr_Occurred() is space.w_ValueError
        state = space.fromcache(State)
        assert space.eq_w(state.operror.get_w_value(space),
                          space.wrap("a value"))

        api.PyErr_Clear()

    def test_SetNone(self, space, api):
        api.PyErr_SetNone(space.w_KeyError)
        state = space.fromcache(State)
        assert space.eq_w(state.operror.w_type, space.w_KeyError)
        assert space.eq_w(state.operror.get_w_value(space), space.w_None)
        api.PyErr_Clear()

        api.PyErr_NoMemory()
        assert space.eq_w(state.operror.w_type, space.w_MemoryError)
        api.PyErr_Clear()

    def test_BadArgument(self, space, api):
        ret = api.PyErr_BadArgument()
        state = space.fromcache(State)
        assert space.eq_w(state.operror.w_type, space.w_TypeError)
        assert ret == 0
        api.PyErr_Clear()

    def test_Warning(self, space, api, capfd):
        message = rffi.str2charp("this is a warning")
        api.PyErr_WarnEx(None, message, 1)
        space.call_method(space.sys.get('stderr'), "flush")
        out, err = capfd.readouterr()
        assert ": UserWarning: this is a warning" in err
        rffi.free_charp(message)

    def test_print_err(self, space, api, capfd):
        api.PyErr_SetObject(space.w_Exception, space.wrap("cpyext is cool"))
        api.PyErr_Print()
        space.call_method(space.sys.get('stderr'), "flush")
        out, err = capfd.readouterr()
        assert "cpyext is cool" in err
        assert not api.PyErr_Occurred()

    def test_WriteUnraisable(self, space, api, capfd):
        api.PyErr_SetObject(space.w_ValueError, space.wrap("message"))
        w_where = space.wrap("location")
        api.PyErr_WriteUnraisable(w_where)
        space.call_method(space.sys.get('stderr'), "flush")
        out, err = capfd.readouterr()
        assert "Exception ValueError: 'message' in 'location' ignored" == err.strip()

    @pytest.mark.skipif(True, reason='not implemented yet')
    def test_interrupt_occurred(self, space, api):
        assert not api.PyOS_InterruptOccurred()
        import signal, os
        recieved = []
        def default_int_handler(*args):
            recieved.append('ok')
        signal.signal(signal.SIGINT, default_int_handler)
        os.kill(os.getpid(), signal.SIGINT)
        assert recieved == ['ok']
        assert api.PyOS_InterruptOccurred()

class AppTestFetch(AppTestCpythonExtensionBase):
    def setup_class(cls):
        from pypy.interpreter.test.test_fsencode import get_special_char
        space = cls.space
        cls.special_char = get_special_char()
        cls.w_special_char = space.wrap(cls.special_char)
        AppTestCpythonExtensionBase.setup_class.im_func(cls)


    def test_occurred(self):
        module = self.import_extension('foo', [
            ("check_error", "METH_NOARGS",
             '''
             PyErr_SetString(PyExc_TypeError, "message");
             PyErr_Occurred();
             PyErr_Clear();
             Py_RETURN_TRUE;
             '''
             ),
            ])
        assert module.check_error()

    def test_fetch_and_restore(self):
        module = self.import_extension('foo', [
            ("check_error", "METH_NOARGS",
             '''
             PyObject *type, *val, *tb;
             PyErr_SetString(PyExc_TypeError, "message");

             PyErr_Fetch(&type, &val, &tb);
             if (PyErr_Occurred())
                 return NULL;
             if (type != PyExc_TypeError)
                 Py_RETURN_FALSE;
             PyErr_Restore(type, val, tb);
             if (!PyErr_Occurred())
                 Py_RETURN_FALSE;
             PyErr_Clear();
             Py_RETURN_TRUE;
             '''
             ),
            ])
        assert module.check_error()


    def test_normalize(self):
        module = self.import_extension('foo', [
            ("check_error", "METH_NOARGS",
             '''
             PyObject *type, *val, *tb;
             PyErr_SetString(PyExc_TypeError, "message");

             PyErr_Fetch(&type, &val, &tb);
             if (type != PyExc_TypeError)
                 Py_RETURN_FALSE;
             if (!PyUnicode_Check(val))
                 Py_RETURN_FALSE;
             /* Normalize */
             PyErr_NormalizeException(&type, &val, &tb);
             if (type != PyExc_TypeError)
                 Py_RETURN_FALSE;
             if ((PyObject*)Py_TYPE(val) != PyExc_TypeError)
                 Py_RETURN_FALSE;

             /* Normalize again */
             PyErr_NormalizeException(&type, &val, &tb);
             if (type != PyExc_TypeError)
                 Py_RETURN_FALSE;
             if ((PyObject*)Py_TYPE(val) != PyExc_TypeError)
                 Py_RETURN_FALSE;

             PyErr_Restore(type, val, tb);
             PyErr_Clear();
             Py_RETURN_TRUE;
             '''
             ),
            ])
        assert module.check_error()

    def test_SetFromErrno(self):
        import sys
        if sys.platform != 'win32':
            skip("callbacks through ll2ctypes modify errno")
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 errno = EBADF;
                 PyErr_SetFromErrno(PyExc_OSError);
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        try:
            module.set_from_errno()
        except OSError as e:
            assert e.errno == errno.EBADF
            assert e.strerror == os.strerror(errno.EBADF)
            assert e.filename is None

    def test_SetFromErrnoWithFilename(self):
        char = self.special_char
        if char is None:
            char = "a" # boring
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilename(PyExc_OSError, "/path/to/file");
                 return NULL;
                 '''),
                ("set_from_errno_special", "METH_NOARGS",
                 '''
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilename(PyExc_OSError, "/path/to/%s");
                 return NULL;
                 ''' % (char, )),
                ],
                prologue="#include <errno.h>")
        exc_info = raises(OSError, module.set_from_errno)
        assert exc_info.value.filename == "/path/to/file"
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

        exc_info = raises(OSError, module.set_from_errno_special)
        assert exc_info.value.filename == "/path/to/%s" % (char, )
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

    def test_SetFromErrnoWithFilename_NULL(self):
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilename(PyExc_OSError, NULL);
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        exc_info = raises(OSError, module.set_from_errno)
        assert exc_info.value.filename is None
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

    def test_SetFromErrnoWithFilenameObject__PyUnicode(self):
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 PyObject *filenameObject = PyUnicode_FromString("/path/to/file");
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, filenameObject);
                 Py_DECREF(filenameObject);
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        exc_info = raises(OSError, module.set_from_errno)
        assert exc_info.value.filename == "/path/to/file"
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

    def test_SetFromErrnoWithFilenameObject__PyLong(self):
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 PyObject *intObject = PyLong_FromLong(3);
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, intObject);
                 Py_DECREF(intObject);
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        exc_info = raises(OSError, module.set_from_errno)
        assert exc_info.value.filename == 3
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

    def test_SetFromErrnoWithFilenameObject__PyList(self):
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 PyObject *lst = Py_BuildValue("[iis]", 1, 2, "three");
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, lst);
                 Py_DECREF(lst);
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        exc_info = raises(OSError, module.set_from_errno)
        assert exc_info.value.filename == [1, 2, "three"]
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

    def test_SetFromErrnoWithFilenameObject__PyTuple(self):
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 PyObject *tuple = Py_BuildValue("(iis)", 1, 2, "three");
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, tuple);
                 Py_DECREF(tuple);
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        exc_info = raises(OSError, module.set_from_errno)
        assert exc_info.value.filename == (1, 2, "three")
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

    def test_SetFromErrnoWithFilenameObject__Py_None(self):
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 PyObject *none = Py_BuildValue("");
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, none);
                 Py_DECREF(none);
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        exc_info = raises(OSError, module.set_from_errno)
        assert exc_info.value.filename is None
        assert exc_info.value.errno == errno.EBADF
        assert exc_info.value.strerror == os.strerror(errno.EBADF)

    def test_PyErr_Display(self):
        from sys import version_info
        if self.runappdirect and (version_info.major < 3 or version_info.minor < 3):
            skip('PyErr_{GS}etExcInfo introduced in python 3.3')
        module = self.import_extension('foo', [
            ("display_error", "METH_VARARGS",
             r'''
             PyObject *type, *val, *tb;
             PyErr_GetExcInfo(&type, &val, &tb);
             PyErr_Display(type, val, tb);
             Py_XDECREF(type);
             Py_XDECREF(val);
             Py_XDECREF(tb);
             Py_RETURN_NONE;
             '''),
            ])
        import io, sys
        sys.stderr = io.StringIO()
        try:
            1 / 0
        except ZeroDivisionError:
            module.display_error()
        finally:
            output = sys.stderr.getvalue()
            sys.stderr = sys.__stderr__
        assert "in test_PyErr_Display\n" in output
        assert "ZeroDivisionError" in output

    @pytest.mark.skipif(True, reason=
        "XXX seems to pass, but doesn't: 'py.test -s' shows errors in PyObject_Free")
    def test_GetSetExcInfo(self):
        import sys
        if self.runappdirect and (sys.version_info.major < 3 or
                                  sys.version_info.minor < 3):
            skip('PyErr_{GS}etExcInfo introduced in python 3.3')
        module = self.import_extension('foo', [
            ("getset_exc_info", "METH_VARARGS",
             r'''
             PyObject *type, *val, *tb;
             PyObject *new_type, *new_val, *new_tb;
             PyObject *result;

             if (!PyArg_ParseTuple(args, "OOO", &new_type, &new_val, &new_tb))
                 return NULL;

             PyErr_GetExcInfo(&type, &val, &tb);

             Py_INCREF(new_type);
             Py_INCREF(new_val);
             Py_INCREF(new_tb);
             PyErr_SetExcInfo(new_type, new_val, new_tb);

             result = Py_BuildValue("OOO",
                                    type ? type : Py_None,
                                    val  ? val  : Py_None,
                                    tb   ? tb   : Py_None);
             Py_XDECREF(type);
             Py_XDECREF(val);
             Py_XDECREF(tb);
             return result;
             '''
             ),
            ])
        try:
            raise ValueError(5)
        except ValueError as old_exc:
            new_exc = TypeError("TEST")
            orig_sys_exc_info = sys.exc_info()
            orig_exc_info = module.getset_exc_info(new_exc.__class__,
                                                   new_exc, None)
            new_sys_exc_info = sys.exc_info()
            new_exc_info = module.getset_exc_info(*orig_exc_info)
            reset_sys_exc_info = sys.exc_info()

            assert orig_exc_info[0] is old_exc.__class__
            assert orig_exc_info[1] is old_exc
            assert orig_exc_info == orig_sys_exc_info
            assert orig_exc_info == reset_sys_exc_info
            assert new_exc_info == (new_exc.__class__, new_exc, None)
            assert new_exc_info == new_sys_exc_info
