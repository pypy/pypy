
/************************************************************/
/***  Generic C header section                            ***/

#include "Python.h"
#include "compile.h"
#include "frameobject.h"
#include "structmember.h"

static PyObject *this_module_globals;

/* Turn this off if you don't want the call trace frames to be built */
#define USE_CALL_TRACE
#if 0
#define OBNOXIOUS_PRINT_STATEMENTS
#endif
#define INSIDE_FUNCTION "<unknown>"

#define op_richcmp(x,y,r,err,dir)   \
					   if (!(r=PyObject_RichCompare(x,y,dir))) goto err;
#define OP_LT(x,y,r,err)  op_richcmp(x,y,r,err, Py_LT)
#define OP_LE(x,y,r,err)  op_richcmp(x,y,r,err, Py_LE)
#define OP_EQ(x,y,r,err)  op_richcmp(x,y,r,err, Py_EQ)
#define OP_NE(x,y,r,err)  op_richcmp(x,y,r,err, Py_NE)
#define OP_GT(x,y,r,err)  op_richcmp(x,y,r,err, Py_GT)
#define OP_GE(x,y,r,err)  op_richcmp(x,y,r,err, Py_GE)

#define OP_IS_(x,y,r,err) r = x == y ? Py_True : Py_False; Py_INCREF(r);

#define OP_IS_TRUE(x,r,err)	switch (PyObject_IsTrue(x)) {	\
				case 0: r=Py_False; break;	\
				case 1: r=Py_True;  break;	\
				default: goto err;		\
				}				\
				Py_INCREF(r);

#define OP_NEG(x,r,err)           if (!(r=PyNumber_Negative(x)))     goto err;
#define OP_POS(x,r,err)           if (!(r=PyNumber_Positive(x)))     goto err;
#define OP_INVERT(x,r,err)        if (!(r=PyNumber_Invert(x)))       goto err;

#define OP_ADD(x,y,r,err)         if (!(r=PyNumber_Add(x,y)))        goto err;
#define OP_SUB(x,y,r,err)         if (!(r=PyNumber_Subtract(x,y)))   goto err;
#define OP_MUL(x,y,r,err)         if (!(r=PyNumber_Multiply(x,y)))   goto err;
#define OP_TRUEDIV(x,y,r,err)     if (!(r=PyNumber_TrueDivide(x,y))) goto err;
#define OP_FLOORDIV(x,y,r,err)    if (!(r=PyNumber_FloorDivide(x,y)))goto err;
#define OP_DIV(x,y,r,err)         if (!(r=PyNumber_Divide(x,y)))     goto err;
#define OP_MOD(x,y,r,err)         if (!(r=PyNumber_Remainder(x,y)))  goto err;
#define OP_POW(x,y,r,err)         if (!(r=PyNumber_Power(x,y,Py_None)))goto err;
#define OP_LSHIFT(x,y,r,err)      if (!(r=PyNumber_Lshift(x,y)))     goto err;
#define OP_RSHIFT(x,y,r,err)      if (!(r=PyNumber_Rshift(x,y)))     goto err;
#define OP_AND_(x,y,r,err)        if (!(r=PyNumber_And(x,y)))        goto err;
#define OP_OR_(x,y,r,err)         if (!(r=PyNumber_Or(x,y)))         goto err;
#define OP_XOR(x,y,r,err)         if (!(r=PyNumber_Xor(x,y)))        goto err;

#define OP_INPLACE_ADD(x,y,r,err) if (!(r=PyNumber_InPlaceAdd(x,y)))           \
								     goto err;
#define OP_INPLACE_SUB(x,y,r,err) if (!(r=PyNumber_InPlaceSubtract(x,y)))      \
								     goto err;
#define OP_INPLACE_MUL(x,y,r,err) if (!(r=PyNumber_InPlaceMultiply(x,y)))      \
								     goto err;
#define OP_INPLACE_TRUEDIV(x,y,r,err) if (!(r=PyNumber_InPlaceTrueDivide(x,y)))\
								     goto err;
#define OP_INPLACE_FLOORDIV(x,y,r,err)if(!(r=PyNumber_InPlaceFloorDivide(x,y)))\
								     goto err;
#define OP_INPLACE_DIV(x,y,r,err) if (!(r=PyNumber_InPlaceDivide(x,y)))        \
								     goto err;
#define OP_INPLACE_MOD(x,y,r,err) if (!(r=PyNumber_InPlaceRemainder(x,y)))     \
								     goto err;
#define OP_INPLACE_POW(x,y,r,err) if (!(r=PyNumber_InPlacePower(x,y,Py_None))) \
								     goto err;
#define OP_INPLACE_LSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceLshift(x,y)))     \
								     goto err;
#define OP_INPLACE_RSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceRshift(x,y)))     \
								     goto err;
#define OP_INPLACE_AND(x,y,r,err)    if (!(r=PyNumber_InPlaceAnd(x,y)))        \
								     goto err;
#define OP_INPLACE_OR(x,y,r,err)     if (!(r=PyNumber_InPlaceOr(x,y)))         \
								     goto err;
#define OP_INPLACE_XOR(x,y,r,err)    if (!(r=PyNumber_InPlaceXor(x,y)))        \
								     goto err;

#define OP_GETITEM(x,y,r,err)     if (!(r=PyObject_GetItem1(x,y)))   goto err;
#define OP_SETITEM(x,y,z,r,err)   if ((PyObject_SetItem1(x,y,z))<0)  goto err; \
				  r=Py_None; Py_INCREF(r);
#define OP_CONTAINS(x,y,r,err)    switch (PySequence_Contains(x,y)) {	\
	case 1:								\
		Py_INCREF(Py_True); r = Py_True; break;			\
	case 0:								\
		Py_INCREF(Py_False); r = Py_False; break;		\
	default: goto err; }

#define OP_GETATTR(x,y,r,err)     if (!(r=PyObject_GetAttr(x,y)))    goto err;
#define OP_SETATTR(x,y,z,r,err)   if ((PyObject_SetAttr(x,y,z))<0)   goto err; \
				  r=Py_None; Py_INCREF(r);
#define OP_DELATTR(x,y,r,err)     if ((PyObject_SetAttr(x,y,NULL))<0)goto err; \
				  r=Py_None; Py_INCREF(r);

#define OP_NEWSLICE(x,y,z,r,err)  if (!(r=PySlice_New(x,y,z)))       goto err;

#define OP_ITER(x,r,err)          if (!(r=PyObject_GetIter(x)))      goto err;
#define OP_NEXT(x,r,err)          if (!(r=PyIter_Next(x))) {                   \
		if (!PyErr_Occurred()) PyErr_SetNone(PyExc_StopIteration);     \
		goto err;                                                      \
	}


/*** tests ***/

#define EQ_False(o)     (o == Py_False)
#define EQ_True(o)      (o == Py_True)
#define EQ_0(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==0)
#define EQ_1(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==1)


/*** misc ***/

#define MOVE(x, y)             y = x;

#define INITCHK(expr)          if (!(expr)) return;


/*** classes ***/

/*#define SETUP_CLASS(t, name, base)				\
	t = PyObject_CallFunction((PyObject*) &PyType_Type,	\
				  "s(O){}", name, base)*/

#define SETUP_CLASS_ATTR(t, attr, value)	\
	(PyObject_SetAttrString(t, attr, value) >= 0)

/*** instances ***/

#define SETUP_INSTANCE_ATTR(t, attr, value)	\
	(PyObject_SetAttrString(t, attr, value) >= 0)

#define SETUP_INSTANCE(i, cls)                  \
	(i = PyType_GenericAlloc((PyTypeObject *)cls, 0))

/* we need a subclass of 'builtin_function_or_method' which can be used
   as methods: builtin function objects that can be bound on instances */
static PyObject *
gencfunc_descr_get(PyObject *func, PyObject *obj, PyObject *type)
{
	if (obj == Py_None)
		obj = NULL;
	return PyMethod_New(func, obj, type);
}
static PyTypeObject PyGenCFunction_Type = {
	PyObject_HEAD_INIT(NULL)
	0,
	"pypy_generated_function",
	sizeof(PyCFunctionObject),
	0,
	0,					/* tp_dealloc */
	0,					/* tp_print */
	0,					/* tp_getattr */
	0,					/* tp_setattr */
	0,					/* tp_compare */
	0,					/* tp_repr */
	0,					/* tp_as_number */
	0,					/* tp_as_sequence */
	0,					/* tp_as_mapping */
	0,					/* tp_hash */
	0,					/* tp_call */
	0,					/* tp_str */
	0,					/* tp_getattro */
	0,					/* tp_setattro */
	0,					/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,			/* tp_flags */
	0,					/* tp_doc */
	0,					/* tp_traverse */
	0,					/* tp_clear */
	0,					/* tp_richcompare */
	0,					/* tp_weaklistoffset */
	0,					/* tp_iter */
	0,					/* tp_iternext */
	0,					/* tp_methods */
	0,					/* tp_members */
	0,					/* tp_getset */
	/*&PyCFunction_Type set below*/ 0,	/* tp_base */
	0,					/* tp_dict */
	gencfunc_descr_get,			/* tp_descr_get */
	0,					/* tp_descr_set */
};

#define MODULE_INITFUNC(modname) \
	static PyMethodDef no_methods[] = { NULL, NULL }; \
	void init##modname(void)

#define SETUP_MODULE(modname)					\
	PyObject *m = Py_InitModule(#modname, no_methods); \
	this_module_globals = PyModule_GetDict(m); \
	PyGenCFunction_Type.tp_base = &PyCFunction_Type;	\
	PyType_Ready(&PyGenCFunction_Type);			\
	PyExc_OperationError = PyErr_NewException(#modname ".OperationError", NULL, NULL);


/*** operations with a variable number of arguments ***/

#define OP_NEWLIST0(r,err)         if (!(r=PyList_New(0))) goto err;
#define OP_NEWLIST(args,r,err)     if (!(r=PyList_Pack args)) goto err;
#define OP_NEWTUPLE(args,r,err)    if (!(r=PyTuple_Pack args)) goto err;

#if defined(USE_CALL_TRACE)

static int callstack_depth = -1;
static PyCodeObject* getcode(char *func_name, char *func_filename, int lineno);
static int trace_frame(PyThreadState *tstate, PyFrameObject *f, int code, PyObject *val);
static int trace_frame_exc(PyThreadState *tstate, PyFrameObject *f);

static PyFrameObject *traced_function_head(PyObject *function, PyObject *args, char *c_signature, char *filename, int c_lineno, PyThreadState *tstate) {
	PyCodeObject *c;
	PyFrameObject *f;
	PyObject *locals;
	PyObject *locals_signature;
	PyObject *locals_lineno;
	PyObject *locals_filename;

	if (function == NULL || args == NULL || tstate == NULL) {
		printf("BAD ARGUMENTS!\n");
		printf("function = 0x%08X args = %08X tstate = %08X\n", function, args, tstate);
		return NULL;
	}
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

static PyObject *traced_function_call(PyObject *allargs, char *c_signature, char *filename, int c_lineno) {
	/*
		STEALS a reference to allargs
	*/
	PyFrameObject *f;
	PyObject *rval;
	PyThreadState *tstate;
	PyObject *function;
	PyObject *args;

	if (allargs == NULL) {
		return NULL;
	}
	args = PyTuple_GetSlice(allargs, 1, PyTuple_Size(allargs));
	function = PyTuple_GetItem(allargs, 0);
	if (args == NULL || function == NULL) {
		return NULL;
	}
	Py_INCREF(function);
	Py_DECREF(allargs);

	tstate = PyThreadState_GET();
	f = traced_function_head(function, args, c_signature, filename, c_lineno, tstate);
	if (f == NULL) {
		Py_DECREF(function);
		Py_DECREF(args);
		return NULL;
	}

	rval = PyObject_Call(function, args, NULL);
	Py_DECREF(function);
	Py_DECREF(args);
	return traced_function_tail(rval, f, tstate);
}

#define OP_SIMPLE_CALL(args, r, err) if ((r = traced_function_call(PyTuple_CrazyPack args, INSIDE_FUNCTION " OP_SIMPLE_CALL" #args, __FILE__, __LINE__)) == NULL) \
					goto err;

#define FUNCTION_HEAD(signature, self, args) \
	PyThreadState *__tstate = PyThreadState_GET(); \
	PyFrameObject *__f = traced_function_head(self, args, signature, __FILE__, __LINE__, __tstate); \
	if (__f == NULL) { \
		printf("frame is null, wtf?!\n"); \
		return NULL; \
	}

#define FUNCTION_RETURN(rval) return traced_function_tail(rval, __f, __tstate);


#else

#define OP_SIMPLE_CALL(args,r,err) if (!(r=PyObject_CallFunctionObjArgs args)) \
					goto err;

#define FUNCTION_HEAD(signature, self, args)
#define FUNCTION_RETURN(rval) return rval;

#endif

static PyObject* PyTuple_CrazyPack(PyObject *begin, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	PyObject *tuple;
	va_list vargs;

	result = PyList_New(0);
	if (result == NULL || begin == NULL) {
		return result;
	}
	va_start(vargs, begin);
	if (PyList_Append(result, begin) == -1) {
		Py_XDECREF(result);
		return result;
	}
	while ((o = va_arg(vargs, PyObject *)) != NULL) {
		if (PyList_Append(result, o) == -1) {
			Py_XDECREF(result);
			return NULL;
		}
	}
	va_end(vargs);
	if ((tuple = PySequence_Tuple(result)) == NULL) {
		Py_DECREF(result);
		return NULL;
	}
	Py_DECREF(result);
	return tuple;
}

static PyObject* PyList_CrazyPack(PyObject *begin, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	va_list vargs;

	result = PyList_New(0);
	if (result == NULL || begin == NULL) {
		return result;
	}
	va_start(vargs, begin);
	if (PyList_Append(result, begin) == -1) {
		Py_XDECREF(result);
		return result;
	}
	while ((o = va_arg(vargs, PyObject *)) != NULL) {
		if (PyList_Append(result, o) == -1) {
			Py_XDECREF(result);
			return NULL;
		}
	}
	va_end(vargs);
	return result;
}


static PyObject* PyList_Pack(int n, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	va_list vargs;

	va_start(vargs, n);
	result = PyList_New(n);
	if (result == NULL) {
		return NULL;
	}
	for (i = 0; i < n; i++) {
		o = va_arg(vargs, PyObject *);
		Py_INCREF(o);
		PyList_SET_ITEM(result, i, o);
	}
	va_end(vargs);
	return result;
}

#if PY_VERSION_HEX < 0x02040000   /* 2.4 */
static PyObject* PyTuple_Pack(int n, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	PyObject **items;
	va_list vargs;

	va_start(vargs, n);
	result = PyTuple_New(n);
	if (result == NULL) {
		return NULL;
	}
	items = ((PyTupleObject *)result)->ob_item;
	for (i = 0; i < n; i++) {
		o = va_arg(vargs, PyObject *);
		Py_INCREF(o);
		items[i] = o;
	}
	va_end(vargs);
	return result;
}
#endif

#if PY_VERSION_HEX >= 0x02030000   /* 2.3 */
# define PyObject_GetItem1  PyObject_GetItem
# define PyObject_SetItem1  PyObject_SetItem
#else
/* for Python 2.2 only */
static PyObject* PyObject_GetItem1(PyObject* obj, PyObject* index)
{
	int start, stop, step;
	if (!PySlice_Check(index)) {
		return PyObject_GetItem(obj, index);
	}
	if (((PySliceObject*) index)->start == Py_None) {
		start = -INT_MAX-1;
	} else {
		start = PyInt_AsLong(((PySliceObject*) index)->start);
		if (start == -1 && PyErr_Occurred()) {
			return NULL;
		}
	}
	if (((PySliceObject*) index)->stop == Py_None) {
		stop = INT_MAX;
	} else {
		stop = PyInt_AsLong(((PySliceObject*) index)->stop);
		if (stop == -1 && PyErr_Occurred()) {
			return NULL;
		}
	}
	if (((PySliceObject*) index)->step != Py_None) {
		step = PyInt_AsLong(((PySliceObject*) index)->step);
		if (step == -1 && PyErr_Occurred()) {
			return NULL;
		}
		if (step != 1) {
			PyErr_SetString(PyExc_ValueError,
					"obj[slice]: no step allowed");
			return NULL;
		}
	}
	return PySequence_GetSlice(obj, start, stop);
}
static PyObject* PyObject_SetItem1(PyObject* obj, PyObject* index, PyObject* v)
{
	int start, stop, step;
	if (!PySlice_Check(index)) {
		return PyObject_SetItem(obj, index, v);
	}
	if (((PySliceObject*) index)->start == Py_None) {
		start = -INT_MAX-1;
	} else {
		start = PyInt_AsLong(((PySliceObject*) index)->start);
		if (start == -1 && PyErr_Occurred()) {
			return NULL;
		}
	}
	if (((PySliceObject*) index)->stop == Py_None) {
		stop = INT_MAX;
	} else {
		stop = PyInt_AsLong(((PySliceObject*) index)->stop);
		if (stop == -1 && PyErr_Occurred()) {
			return NULL;
		}
	}
	if (((PySliceObject*) index)->step != Py_None) {
		step = PyInt_AsLong(((PySliceObject*) index)->step);
		if (step == -1 && PyErr_Occurred()) {
			return NULL;
		}
		if (step != 1) {
			PyErr_SetString(PyExc_ValueError,
					"obj[slice]: no step allowed");
			return NULL;
		}
	}
	return PySequence_SetSlice(obj, start, stop, v);
}
#endif

static PyObject* PyExc_OperationError;

#ifdef USE_CALL_TRACE
static int
trace_frame(PyThreadState *tstate, PyFrameObject *f, int code, PyObject *val)
{
	int result = 0;
	if (!tstate->use_tracing || tstate->tracing) {
		return 0;
	}
	if (tstate->c_profilefunc != NULL) {
		tstate->tracing++;
		result = tstate->c_profilefunc(tstate->c_profileobj,
						   f, code , val);
		tstate->use_tracing = ((tstate->c_tracefunc != NULL)
					   || (tstate->c_profilefunc != NULL));
		tstate->tracing--;
		if (result) {
			return result;
		}
	}
	if (tstate->c_tracefunc != NULL) {
		tstate->tracing++;
		result = tstate->c_tracefunc(tstate->c_traceobj,
						 f, code , val);
		tstate->use_tracing = ((tstate->c_tracefunc != NULL)
					   || (tstate->c_profilefunc != NULL));
		tstate->tracing--;
	}   
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
	int i;

#if defined(OBNOXIOUS_PRINT_STATEMENTS)
	printf("%5d: ", lineno);
	assert(callstack_depth >= 0);
	if (callstack_depth) {
		for (i=0; i<callstack_depth; ++i) {
			printf("  ");
		}
	}
	printf("%s\n", func_name);
#endif
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
#endif

/************************************************************/
/***  The rest is produced by genc.py                     ***/
