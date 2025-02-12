from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestFrameObject(AppTestCpythonExtensionBase):

    def test_forge_frame(self):
        module = self.import_extension('foo', [
            ("raise_exception", "METH_NOARGS",
             """
                 PyObject *py_srcfile = PyUnicode_FromString("filename");
                 PyObject *py_funcname = PyUnicode_FromString("funcname");
                 PyObject *py_globals = PyDict_New();
                 PyObject *py_locals = PyDict_New();
                 PyObject *empty_bytes = PyBytes_FromString("");
                 PyObject *empty_tuple = PyTuple_New(0);
                 PyCodeObject *py_code;
                 PyFrameObject *py_frame = NULL;

                 py_code = (PyCodeObject *)PyCode_New(
                     0,            /*int argcount,*/
                     #if PY_MAJOR_VERSION >= 3
                     0,            /*int kwonlyargcount,*/
                     #endif
                     0,            /*int nlocals,*/
                     0,            /*int stacksize,*/
                     0,            /*int flags,*/
                     empty_bytes,  /*PyObject *code,*/
                     empty_tuple,  /*PyObject *consts,*/
                     empty_tuple,  /*PyObject *names,*/
                     empty_tuple,  /*PyObject *varnames,*/
                     empty_tuple,  /*PyObject *freevars,*/
                     empty_tuple,  /*PyObject *cellvars,*/
                     py_srcfile,   /*PyObject *filename,*/
                     py_funcname,   /*PyObject *qualname,*/
                     py_funcname,  /*PyObject *name,*/
                     42,           /*int firstlineno,*/
                     empty_bytes   /*PyObject *lnotab*/
                 );

                 if (!py_code) goto bad;
                 py_frame = PyFrame_New(
                     PyThreadState_Get(), /*PyThreadState *tstate,*/
                     py_code,             /*PyCodeObject *code,*/
                     py_globals,          /*PyObject *globals,*/
                     py_locals            /*PyObject *locals*/
                 );
                 if (!py_frame) goto bad;
                 py_frame->f_lineno = 48; /* Does not work with CPython */
                 PyErr_SetString(PyExc_ValueError, "error message");
                 PyTraceBack_Here(py_frame);
             bad:
                 Py_XDECREF(py_srcfile);
                 Py_XDECREF(py_funcname);
                 Py_XDECREF(empty_bytes);
                 Py_XDECREF(empty_tuple);
                 Py_XDECREF(py_globals);
                 Py_XDECREF(py_locals);
                 Py_XDECREF(py_code);
                 Py_XDECREF(py_frame);
                 return NULL;
             """),
            ], prologue='#include "frameobject.h"')
        exc = raises(ValueError, module.raise_exception)
        exc.value.args[0] == 'error message'
        frame = exc.traceback.tb_frame
        if not self.runappdirect:
            frame = exc.traceback.tb_frame
            assert frame.f_code.co_filename == "filename"
            assert frame.f_code.co_name == "funcname"

            # Cython does not work on CPython as well...
            assert exc.traceback.tb_lineno in (-1, 42, 48) # should be 48
            assert frame.f_lineno in (-1, 42, 48)

    def test_forge_frame_newer(self):
        module = self.import_extension('foo', [
            ("raise_exception", "METH_NOARGS",
             """
                 PyCodeObject *py_code = NULL;
                 PyFrameObject *py_frame = NULL;
                 PyObject *py_globals = NULL;

                 py_code = PyCode_NewEmpty(
                    "filename", "funcname", 42);
                 py_globals = PyDict_New();

                 py_frame = PyFrame_New(
                     PyThreadState_Get(), /*PyThreadState *tstate,*/
                     py_code,             /*PyCodeObject *code,*/
                     py_globals,          /*PyObject *globals,*/
                     NULL                 /*PyObject *locals*/
                 );
                 PyErr_SetString(PyExc_ValueError, "error message");
                 PyTraceBack_Here(py_frame);

                 Py_XDECREF(py_globals);
                 Py_XDECREF(py_code);
                 Py_XDECREF(py_frame);
                 return NULL;
             """),
            ], prologue='#include "frameobject.h"')
        exc = raises(ValueError, module.raise_exception)
        exc.value.args[0] == 'error message'
        frame = exc.traceback.tb_frame
        if not self.runappdirect:
            assert frame.f_code.co_filename == "filename"
            assert frame.f_code.co_name == "funcname"

            assert exc.traceback.tb_lineno == 42
            assert frame.f_lineno == 42


    def test_traceback_check(self):
        module = self.import_extension('foo', [
            ("traceback_check", "METH_NOARGS",
             """
                 int check;
                 PyObject *type, *value, *tb;
                 PyObject *ret = PyRun_String("XXX", Py_eval_input,
                                              Py_None, Py_None);
                 if (ret) {
                     Py_DECREF(ret);
                     PyErr_SetString(PyExc_AssertionError, "should raise");
                     return NULL;
                 }
                 PyErr_Fetch(&type, &value, &tb);
                 if (tb == NULL) {
                     Py_XDECREF(type);
                     Py_XDECREF(value);
                     PyErr_SetString(PyExc_AssertionError, "No traceback");
                     return NULL;
                 }
                 check = PyTraceBack_Check(tb);
                 Py_XDECREF(type);
                 Py_XDECREF(value);
                 Py_XDECREF(tb);
                 if (check) {
                     Py_RETURN_TRUE;
                 }
                 else {
                     Py_RETURN_FALSE;
                 }
             """),
            ])
        # On CPython the traceback is NULL
        assert module.traceback_check()

    def test_get_xxx(self):
        module = self.import_extension('foo', [
            ("frame_getlocals", "METH_O",
             """
                if (!PyFrame_Check(args)) {
                    PyErr_SetString(PyExc_TypeError, "argument must be a frame");
                    return NULL;
                }
                return PyFrame_GetLocals((PyFrameObject *)args);

             """),
            ("frame_getglobals", "METH_O",
             """
                if (!PyFrame_Check(args)) {
                    PyErr_SetString(PyExc_TypeError, "argument must be a frame");
                    return NULL;
                }
                return PyFrame_GetGlobals((PyFrameObject *)args);
             """),
            ("frame_getgenerator", "METH_O",
             """
                if (!PyFrame_Check(args)) {
                    PyErr_SetString(PyExc_TypeError, "argument must be a frame");
                    return NULL;
                }
                return PyFrame_GetGenerator((PyFrameObject *)args);
             """),
            ("frame_getbuiltins", "METH_O",
             """
                if (!PyFrame_Check(args)) {
                    PyErr_SetString(PyExc_TypeError, "argument must be a frame");
                    return NULL;
                }
                return PyFrame_GetBuiltins((PyFrameObject *)args);
             """),
            ("frame_getlasti", "METH_O",
             """
                if (!PyFrame_Check(args)) {
                    PyErr_SetString(PyExc_TypeError, "argument must be a frame");
                    return NULL;
                }
                int lasti = PyFrame_GetLasti((PyFrameObject *)args);
                if (lasti < 0) {
                    assert(lasti == -1);
                    Py_RETURN_NONE;
                }
                return PyLong_FromLong(lasti);
             """),
            ("frame_getlinenumber", "METH_O",
             """
                if (!PyFrame_Check(args)) {
                    PyErr_SetString(PyExc_TypeError, "argument must be a frame");
                    return NULL;
                }
                int num = PyFrame_GetLineNumber((PyFrameObject *)args);
                if (num < 0) {
                    Py_RETURN_NONE;
                }
                return PyLong_FromLong(num);
             """),
            ])
        import sys
        frame = sys._getframe()
        assert frame.f_locals == module.frame_getlocals(frame) 
        assert frame.f_globals == module.frame_getglobals(frame) 
        assert frame.f_builtins == module.frame_getbuiltins(frame)
        lasti = module.frame_getlasti(frame) 
        assert abs(frame.f_lasti - lasti) < 40
        assert frame.f_lineno == module.frame_getlinenumber(frame)

        def getgenframe():
            yield sys._getframe()

        gen = getgenframe()
        frame = next(gen)
        assert gen == module.frame_getgenerator(frame)
        
        
        
        
        
