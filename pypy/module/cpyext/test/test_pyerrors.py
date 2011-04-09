import sys
import StringIO

from pypy.module.cpyext.state import State
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.rpython.lltypesystem import rffi, ll2ctypes

from pypy.interpreter.gateway import interp2app

class TestExceptions(BaseApiTest):
    def test_GivenExceptionMatches(self, space, api):
        old_style_exception = space.appexec([], """():
            class OldStyle:
                pass
            return OldStyle
        """)
        exc_matches = api.PyErr_GivenExceptionMatches

        string_exception = space.wrap('exception')
        instance = space.call_function(space.w_ValueError)
        old_style_instance = space.call_function(old_style_exception)
        assert exc_matches(string_exception, string_exception)
        assert exc_matches(old_style_exception, old_style_exception)
        assert not exc_matches(old_style_exception, space.w_Exception)
        assert exc_matches(instance, space.w_ValueError)
        assert exc_matches(old_style_instance, old_style_exception)
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
        api.PyErr_BadArgument()
        state = space.fromcache(State)
        assert space.eq_w(state.operror.w_type, space.w_TypeError)
        api.PyErr_Clear()

    def test_Warning(self, space, api, capfd):
        message = rffi.str2charp("this is a warning")
        api.PyErr_WarnEx(None, message, 1)
        out, err = capfd.readouterr()
        assert ": UserWarning: this is a warning" in err
        rffi.free_charp(message)

    def test_print_err(self, space, api, capfd):
        api.PyErr_SetObject(space.w_Exception, space.wrap("cpyext is cool"))
        api.PyErr_Print()
        out, err = capfd.readouterr()
        assert "cpyext is cool" in err
        assert not api.PyErr_Occurred()

    def test_WriteUnraisable(self, space, api, capfd):
        api.PyErr_SetObject(space.w_ValueError, space.wrap("message"))
        w_where = space.wrap("location")
        api.PyErr_WriteUnraisable(w_where)
        out, err = capfd.readouterr()
        assert "Exception ValueError: 'message' in 'location' ignored" == err.strip()

    def test_ExceptionInstance_Class(self, space, api):
        instance = space.call_function(space.w_ValueError)
        assert api.PyExceptionInstance_Class(instance) is space.w_ValueError

class AppTestFetch(AppTestCpythonExtensionBase):
    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)
        space = cls.space

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
             if (!PyString_Check(val))
                 Py_RETURN_FALSE;
             /* Normalize */
             PyErr_NormalizeException(&type, &val, &tb);
             if (type != PyExc_TypeError)
                 Py_RETURN_FALSE;
             if (val->ob_type != PyExc_TypeError)
                 Py_RETURN_FALSE;

             /* Normalize again */
             PyErr_NormalizeException(&type, &val, &tb);
             if (type != PyExc_TypeError)
                 Py_RETURN_FALSE;
             if (val->ob_type != PyExc_TypeError)
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
        except OSError, e:
            assert e.errno == errno.EBADF
            assert e.strerror == os.strerror(errno.EBADF)
            assert e.filename == None

    def test_SetFromErrnoWithFilename(self):
        import sys
        if sys.platform != 'win32':
            skip("callbacks through ll2ctypes modify errno")
        import errno, os

        module = self.import_extension('foo', [
                ("set_from_errno", "METH_NOARGS",
                 '''
                 errno = EBADF;
                 PyErr_SetFromErrnoWithFilename(PyExc_OSError, "blyf");
                 return NULL;
                 '''),
                ],
                prologue="#include <errno.h>")
        try:
            module.set_from_errno()
        except OSError, e:
            assert e.filename == "blyf"
            assert e.errno == errno.EBADF
            assert e.strerror == os.strerror(errno.EBADF)
