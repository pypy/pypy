
/************************************************************/
 /***  C header subsection: pdb tracing of calls           ***/

/* Set genc_funcdef.USE_CALL_TRACE if you want call trace frames to be built */

#if 0
#define OBNOXIOUS_PRINT_STATEMENTS
#endif


/***  Interface  ***/

#if defined(USE_CALL_TRACE)

#define TRACE_CALL       __f, __tstate
#define TRACE_ARGS       PyFrameObject *__f, PyThreadState *__tstate

#define FUNCTION_HEAD(signature, self, args, names, file, line) \
	PyThreadState *__tstate = PyThreadState_GET(); \
	PyObject *__localnames = PyList_CrazyStringPack names; \
	PyFrameObject *__f = traced_function_head(self, args, signature, file, line, __tstate, __localnames);

#define FUNCTION_CHECK() \
	assert (__f != NULL);

#define ERR_DECREF(arg) { if (__f->f_locals) { PyDict_SetItemString(__f->f_locals, #arg, arg); } Py_DECREF(arg); }

#define FUNCTION_RETURN(rval) return traced_function_tail(rval, __f, __tstate);

#else /* !defined(USE_CALL_TRACE) */

#endif /* defined(USE_CALL_TRACE) */


/***  Implementation  ***/

#ifndef PYPY_NOT_MAIN_FILE

#if defined(USE_CALL_TRACE)

static int callstack_depth = -1;
static PyCodeObject* getcode(char *func_name, char *func_filename, int lineno);
static int trace_frame(PyThreadState *tstate, PyFrameObject *f, int code, PyObject *val);
static int trace_frame_exc(PyThreadState *tstate, PyFrameObject *f);

static int
trace_frame(PyThreadState *tstate, PyFrameObject *f, int code, PyObject *val)
{
	int result = 0;
	if (!tstate->use_tracing || tstate->tracing) {
		/*printf("if (!tstate->use_tracing || tstate->tracing)\n");*/
		return 0;
	}
	if (tstate->c_profilefunc != NULL) {
		/*printf("if (tstate->c_profilefunc != NULL)\n");*/
		tstate->tracing++;
		result = tstate->c_profilefunc(tstate->c_profileobj,
						   f, code , val);
		tstate->use_tracing = ((tstate->c_tracefunc != NULL)
					   || (tstate->c_profilefunc != NULL));
		tstate->tracing--;
		if (result) {
			/*printf("	if (result)\n");*/
			return result;
		}
	}
	if (tstate->c_tracefunc != NULL) {
		/*printf("if (tstate->c_tracefunc != NULL)\n");*/
		tstate->tracing++;
		result = tstate->c_tracefunc(tstate->c_traceobj,
						 f, code , val);
		tstate->use_tracing = ((tstate->c_tracefunc != NULL)
					   || (tstate->c_profilefunc != NULL));
		tstate->tracing--;
	}   
	/*printf("return result;\n");*/
	return result;
}

static int
trace_frame_exc(PyThreadState *tstate, PyFrameObject *f)
{
	PyObject *type, *value, *traceback, *arg;
	int err;

	if (tstate->c_tracefunc == NULL) {
		return 0;
	}

	PyErr_Fetch(&type, &value, &traceback);
	if (value == NULL) {
		value = Py_None;
		Py_INCREF(value);
	}
	arg = PyTuple_Pack(3, type, value, traceback);
	if (arg == NULL) {
		PyErr_Restore(type, value, traceback);
		return 0;
	}
	err = trace_frame(tstate, f, PyTrace_EXCEPTION, arg);
	Py_DECREF(arg);
	if (err == 0) {
		PyErr_Restore(type, value, traceback);
	} else {
		Py_XDECREF(type);
		Py_XDECREF(value);
		Py_XDECREF(traceback);
	}
	return err;
}

static PyCodeObject*
getcode(char *func_name, char *func_filename, int lineno)
{
	PyObject *code = NULL;
	PyObject *name = NULL;
	PyObject *nulltuple = NULL;
	PyObject *filename = NULL;
	PyCodeObject *tb_code = NULL;
#if defined(OBNOXIOUS_PRINT_STATEMENTS)
	int i;

	printf("%5d: ", lineno);
	assert(callstack_depth >= 0);
	if (callstack_depth) {
		for (i=0; i<callstack_depth; ++i) {
			printf("  ");
		}
	}
	printf("%s\n", func_name);
#endif /* !defined(OBNOXIOUS_PRINT_STATEMENTS) */

	code = PyString_FromString("");
	if (code == NULL)
		goto failed;
	name = PyString_FromString(func_name);
	if (name == NULL)
		goto failed;
	nulltuple = PyTuple_New(0);
	if (nulltuple == NULL)
		goto failed;
	filename = PyString_FromString(func_filename);
	tb_code = PyCode_New(0,       /* argcount */
						 0,       /* nlocals */
						 0,       /* stacksize */
						 0,       /* flags */
						 code,        /* code */
						 nulltuple,   /* consts */
						 nulltuple,   /* names */
						 nulltuple,   /* varnames */
						 nulltuple,   /* freevars */
						 nulltuple,   /* cellvars */
						 filename,    /* filename */
						 name,        /* name */
						 lineno,      /* firstlineno */
						 code     /* lnotab */
						 );
	if (tb_code == NULL)
		goto failed;
	Py_DECREF(code);
	Py_DECREF(nulltuple);
	Py_DECREF(filename);
	Py_DECREF(name);
	return tb_code;
failed:
	Py_XDECREF(code);
	Py_XDECREF(name);
	return NULL;
}

static PyFrameObject *traced_function_head(PyObject *function, PyObject *args, char *c_signature, char *filename, int c_lineno, PyThreadState *tstate, PyObject *extra_local_names) {
	/*
		STEALS a reference to extra_local_names if not NULL
	*/

	PyCodeObject *c;
	PyFrameObject *f;
	PyObject *locals;
	PyObject *locals_signature;
	PyObject *locals_lineno;
	PyObject *locals_filename;

	assert(function && args && tstate);

	locals = PyDict_New();
	locals_signature = PyString_FromString(c_signature);
	locals_lineno = PyInt_FromLong(c_lineno);
	locals_filename = PyString_FromString(filename);
	if (locals == NULL || function == NULL || args == NULL || 
		locals_signature == NULL || locals_lineno == NULL ||
		locals_filename == NULL) {
		Py_XDECREF(locals);
		Py_XDECREF(locals_signature);
		Py_XDECREF(locals_lineno);
		Py_XDECREF(locals_filename);
		return NULL;
	}
	PyDict_SetItemString(locals, "function", function);
	PyDict_SetItemString(locals, "args", args);
	PyDict_SetItemString(locals, "signature", locals_signature);
	PyDict_SetItemString(locals, "lineno", locals_lineno);
	PyDict_SetItemString(locals, "filename", locals_filename);
	Py_DECREF(locals_signature);
	Py_DECREF(locals_lineno);
	Py_DECREF(locals_filename);
	if (extra_local_names != NULL) {
		int max_locals = MIN(PyList_Size(extra_local_names), PyTuple_Size(args));
        int i;
		for (i = 0; i < max_locals; ++i) {
			PyDict_SetItem(locals, PyList_GET_ITEM(extra_local_names, i), PyTuple_GET_ITEM(args, i));
		}
		Py_DECREF(extra_local_names);
	}

	callstack_depth++;
	c = getcode(c_signature, filename, c_lineno);
	if (c == NULL) {
		Py_DECREF(locals);
		callstack_depth--;
		return NULL;
	}
	f = PyFrame_New(tstate, c, this_module_globals, locals);
	if (f == NULL) {
		callstack_depth--;
		return NULL;
	}
	Py_DECREF(c);
	Py_DECREF(locals);
	tstate->frame = f;
	if (trace_frame(tstate, f, PyTrace_CALL, Py_None) < 0) {
		Py_DECREF(args);
		callstack_depth--;
		return NULL;
	}

	return f;
}

static PyObject *traced_function_tail(PyObject *rval, PyFrameObject *f, PyThreadState *tstate) {
	/*
		STEALS a reference to f
	*/
	if (f == NULL) {
		goto bad_args;
	}
	if (rval == NULL) {
		if (tstate->curexc_traceback == NULL) {
			PyTraceBack_Here(f);
		}
		if (trace_frame_exc(tstate, f) < 0) {
			goto end;
		}
	} else {
		if (trace_frame(tstate, f, PyTrace_RETURN, rval) < 0) {
			Py_DECREF(rval);
			rval = NULL;
		}
	}
end:
	tstate->frame = f->f_back;
	Py_DECREF(f);
bad_args:
	callstack_depth--;
	return rval;
}

static PyObject* PyList_CrazyStringPack(char *begin, ...)
{
	PyObject *o;
	PyObject *result;
	va_list vargs;

	result = PyList_New(0);
	if (result == NULL || begin == NULL) {
		return result;
	}
	va_start(vargs, begin);
	o = PyString_FromString(begin);
	if (o == NULL) {
		Py_XDECREF(result);
		return NULL;
	}
	if (PyList_Append(result, o) == -1) {
		Py_DECREF(o);
		Py_XDECREF(result);
		return result;
	}
	Py_DECREF(o);
	while ((begin = va_arg(vargs, char *)) != NULL) {
		o = PyString_FromString(begin);
		if (o == NULL) {
			Py_XDECREF(result);
			return NULL;
		}
		if (PyList_Append(result, o) == -1) {
			Py_DECREF(o);
			Py_XDECREF(result);
			return NULL;
		}
		Py_DECREF(o);
	}
	va_end(vargs);
	return result;
}

#endif /* defined(USE_CALL_TRACE) */

#endif /* PYPY_NOT_MAIN_FILE */
