from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.eval import (
    Py_single_input, Py_file_input, Py_eval_input)
from pypy.module.cpyext.api import fopen, fclose, fileno, Py_ssize_tP
from pypy.interpreter.gateway import interp2app
from pypy.tool.udir import udir
import sys, os

class TestEval(BaseApiTest):
    def test_eval(self, space, api):
        w_l, w_f = space.fixedview(space.appexec([], """():
        l = []
        def f(arg1, arg2):
            l.append(arg1)
            l.append(arg2)
            return len(l)
        return l, f
        """))

        w_t = space.newtuple([space.wrap(1), space.wrap(2)])
        w_res = api.PyEval_CallObjectWithKeywords(w_f, w_t, None)
        assert space.int_w(w_res) == 2
        assert space.len_w(w_l) == 2
        w_f = space.appexec([], """():
            def f(*args, **kwds):
                assert isinstance(kwds, dict)
                assert 'xyz' in kwds
                return len(kwds) + len(args) * 10
            return f
            """)
        w_t = space.newtuple([space.w_None, space.w_None])
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("xyz"), space.wrap(3))
        w_res = api.PyEval_CallObjectWithKeywords(w_f, w_t, w_d)
        assert space.int_w(w_res) == 21

    def test_call_object(self, space, api):
        w_l, w_f = space.fixedview(space.appexec([], """():
        l = []
        def f(arg1, arg2):
            l.append(arg1)
            l.append(arg2)
            return len(l)
        return l, f
        """))

        w_t = space.newtuple([space.wrap(1), space.wrap(2)])
        w_res = api.PyObject_CallObject(w_f, w_t)
        assert space.int_w(w_res) == 2
        assert space.len_w(w_l) == 2

        w_f = space.appexec([], """():
            def f(*args):
                assert isinstance(args, tuple)
                return len(args) + 8
            return f
            """)

        w_t = space.newtuple([space.wrap(1), space.wrap(2)])
        w_res = api.PyObject_CallObject(w_f, w_t)

        assert space.int_w(w_res) == 10

    def test_run_simple_string(self, space, api):
        def run(code):
            buf = rffi.str2charp(code)
            try:
                return api.PyRun_SimpleString(buf)
            finally:
                rffi.free_charp(buf)

        assert 0 == run("42 * 43")
        
        assert -1 == run("4..3 * 43")
        
        assert api.PyErr_Occurred()
        api.PyErr_Clear()
        
    def test_run_string(self, space, api):
        def run(code, start, w_globals, w_locals):
            buf = rffi.str2charp(code)
            try:
                return api.PyRun_String(buf, start, w_globals, w_locals)
            finally:
                rffi.free_charp(buf)

        w_globals = space.newdict()
        assert 42 * 43 == space.unwrap(
            run("42 * 43", Py_eval_input, w_globals, w_globals))
        assert api.PyObject_Size(w_globals) == 0

        assert run("a = 42 * 43", Py_single_input,
                   w_globals, w_globals) == space.w_None
        assert 42 * 43 == space.unwrap(
            api.PyObject_GetItem(w_globals, space.wrap("a")))

    def test_run_file(self, space, api):
        filepath = udir / "cpyext_test_runfile.py"
        filepath.write("raise ZeroDivisionError")
        fp = fopen(str(filepath), "rb")
        filename = rffi.str2charp(str(filepath))
        w_globals = w_locals = space.newdict()
        api.PyRun_File(fp, filename, Py_file_input, w_globals, w_locals)
        fclose(fp)
        assert api.PyErr_Occurred() is space.w_ZeroDivisionError
        api.PyErr_Clear()

        # try again, but with a closed file
        fp = fopen(str(filepath), "rb")
        os.close(fileno(fp))
        api.PyRun_File(fp, filename, Py_file_input, w_globals, w_locals)
        fclose(fp)
        assert api.PyErr_Occurred() is space.w_IOError
        api.PyErr_Clear()

        rffi.free_charp(filename)

    def test_getbuiltins(self, space, api):
        assert api.PyEval_GetBuiltins() is space.builtin.w_dict

        def cpybuiltins(space):
            return api.PyEval_GetBuiltins()
        w_cpybuiltins = space.wrap(interp2app(cpybuiltins))

        w_result = space.appexec([w_cpybuiltins], """(cpybuiltins):
            return cpybuiltins() is __builtins__.__dict__
        """)
        assert space.is_true(w_result)

        w_result = space.appexec([w_cpybuiltins], """(cpybuiltins):
            d = dict(__builtins__={'len':len}, cpybuiltins=cpybuiltins)
            return eval("cpybuiltins()", d, d)
        """)
        assert space.len_w(w_result) == 1

    def test_getglobals(self, space, api):
        assert api.PyEval_GetLocals() is None
        assert api.PyEval_GetGlobals() is None

        def cpyvars(space):
            return space.newtuple([api.PyEval_GetGlobals(),
                                   api.PyEval_GetLocals()])
        w_cpyvars = space.wrap(interp2app(cpyvars))

        w_result = space.appexec([w_cpyvars], """(cpyvars):
            x = 1
            return cpyvars()
        \ny = 2
        """)
        globals, locals = space.unwrap(w_result)
        assert sorted(locals) == ['cpyvars', 'x']
        assert sorted(globals) == ['__builtins__', 'anonymous', 'y']

    def test_sliceindex(self, space, api):
        pi = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')
        assert api._PyEval_SliceIndex(space.w_None, pi) == 0
        api.PyErr_Clear()

        assert api._PyEval_SliceIndex(space.wrap(123), pi) == 1
        assert pi[0] == 123

        assert api._PyEval_SliceIndex(space.wrap(1 << 66), pi) == 1
        assert pi[0] == sys.maxint

        lltype.free(pi, flavor='raw')

    def test_atexit(self, space, api):
        lst = []
        def func():
            lst.append(42)
        api.Py_AtExit(func)
        cpyext = space.getbuiltinmodule('cpyext')
        cpyext.shutdown(space) # simulate shutdown
        assert lst == [42]

class AppTestCall(AppTestCpythonExtensionBase):
    def test_CallFunction(self):
        module = self.import_extension('foo', [
            ("call_func", "METH_VARARGS",
             """
                return PyObject_CallFunction(PyTuple_GetItem(args, 0),
                   "siO", "text", 42, Py_None);
             """),
            ("call_method", "METH_VARARGS",
             """
                return PyObject_CallMethod(PyTuple_GetItem(args, 0),
                   "count", "s", "t");
             """),
            ])
        def f(*args):
            return args
        assert module.call_func(f) == ("text", 42, None)
        assert module.call_method("text") == 2

    def test_CallFunctionObjArgs(self):
        module = self.import_extension('foo', [
            ("call_func", "METH_VARARGS",
             """
                PyObject *t = PyString_FromString("t");
                PyObject *res = PyObject_CallFunctionObjArgs(
                   PyTuple_GetItem(args, 0),
                   Py_None, NULL);
                Py_DECREF(t);
                return res;
             """),
            ("call_method", "METH_VARARGS",
             """
                PyObject *t = PyString_FromString("t");
                PyObject *count = PyString_FromString("count");
                PyObject *res = PyObject_CallMethodObjArgs(
                   PyTuple_GetItem(args, 0),
                   count, t, NULL);
                Py_DECREF(t);
                Py_DECREF(count);
                return res;
             """),
            ])
        def f(*args):
            return args
        assert module.call_func(f) == (None,)
        assert module.call_method("text") == 2
        
