
/************************************************************/
/***  Generic C header section                            ***/

#include "Python.h"
#include "compile.h"
#include "frameobject.h"
#include "structmember.h"
#include "traceback.h"
#include "marshal.h"
#include "eval.h"

#if !defined(MIN)
#define MIN(a,b) (((a)<(b))?(a):(b))
#endif /* MIN */

static PyObject *this_module_globals;

/* Set this if you want call trace frames to be built */
#if 0
#define USE_CALL_TRACE
#endif

#if 0
#define OBNOXIOUS_PRINT_STATEMENTS
#endif

#define op_bool(r,err,what) { \
		int _retval = what; \
		if (_retval < 0) { \
			FAIL(err) \
		} \
		r = PyBool_FromLong(_retval); \
	}

#define op_richcmp(x,y,r,err,dir) \
					if (!(r=PyObject_RichCompare(x,y,dir))) FAIL(err)
#define OP_LT(x,y,r,err)  op_richcmp(x,y,r,err, Py_LT)
#define OP_LE(x,y,r,err)  op_richcmp(x,y,r,err, Py_LE)
#define OP_EQ(x,y,r,err)  op_richcmp(x,y,r,err, Py_EQ)
#define OP_NE(x,y,r,err)  op_richcmp(x,y,r,err, Py_NE)
#define OP_GT(x,y,r,err)  op_richcmp(x,y,r,err, Py_GT)
#define OP_GE(x,y,r,err)  op_richcmp(x,y,r,err, Py_GE)

#define OP_IS_(x,y,r,err) op_bool(r,err,(x == y))

#define OP_IS_TRUE(x,r,err) op_bool(r,err,PyObject_IsTrue(x))

#define OP_LEN(x,r,err) { \
		int _retval = PyObject_Size(x); \
		if (_retval < 0) { \
			FAIL(err) \
		} \
		r = PyInt_FromLong(_retval); \
	}
#define OP_NEG(x,r,err)           if (!(r=PyNumber_Negative(x)))     FAIL(err)
#define OP_POS(x,r,err)           if (!(r=PyNumber_Positive(x)))     FAIL(err)
#define OP_INVERT(x,r,err)        if (!(r=PyNumber_Invert(x)))       FAIL(err)

#define OP_ADD(x,y,r,err)         if (!(r=PyNumber_Add(x,y)))        FAIL(err)
#define OP_SUB(x,y,r,err)         if (!(r=PyNumber_Subtract(x,y)))   FAIL(err)
#define OP_MUL(x,y,r,err)         if (!(r=PyNumber_Multiply(x,y)))   FAIL(err)
#define OP_TRUEDIV(x,y,r,err)     if (!(r=PyNumber_TrueDivide(x,y))) FAIL(err)
#define OP_FLOORDIV(x,y,r,err)    if (!(r=PyNumber_FloorDivide(x,y)))FAIL(err)
#define OP_DIV(x,y,r,err)         if (!(r=PyNumber_Divide(x,y)))     FAIL(err)
#define OP_MOD(x,y,r,err)         if (!(r=PyNumber_Remainder(x,y)))  FAIL(err)
#define OP_POW(x,y,z,r,err)       if (!(r=PyNumber_Power(x,y,z)))    FAIL(err)
#define OP_LSHIFT(x,y,r,err)      if (!(r=PyNumber_Lshift(x,y)))     FAIL(err)
#define OP_RSHIFT(x,y,r,err)      if (!(r=PyNumber_Rshift(x,y)))     FAIL(err)
#define OP_AND_(x,y,r,err)        if (!(r=PyNumber_And(x,y)))        FAIL(err)
#define OP_OR_(x,y,r,err)         if (!(r=PyNumber_Or(x,y)))         FAIL(err)
#define OP_XOR(x,y,r,err)         if (!(r=PyNumber_Xor(x,y)))        FAIL(err)

#define OP_INPLACE_ADD(x,y,r,err) if (!(r=PyNumber_InPlaceAdd(x,y)))           \
								     FAIL(err)
#define OP_INPLACE_SUB(x,y,r,err) if (!(r=PyNumber_InPlaceSubtract(x,y)))      \
								     FAIL(err)
#define OP_INPLACE_MUL(x,y,r,err) if (!(r=PyNumber_InPlaceMultiply(x,y)))      \
								     FAIL(err)
#define OP_INPLACE_TRUEDIV(x,y,r,err) if (!(r=PyNumber_InPlaceTrueDivide(x,y)))\
								     FAIL(err)
#define OP_INPLACE_FLOORDIV(x,y,r,err)if(!(r=PyNumber_InPlaceFloorDivide(x,y)))\
								     FAIL(err)
#define OP_INPLACE_DIV(x,y,r,err) if (!(r=PyNumber_InPlaceDivide(x,y)))        \
								     FAIL(err)
#define OP_INPLACE_MOD(x,y,r,err) if (!(r=PyNumber_InPlaceRemainder(x,y)))     \
								     FAIL(err)
#define OP_INPLACE_POW(x,y,r,err) if (!(r=PyNumber_InPlacePower(x,y,Py_None))) \
								     FAIL(err)
#define OP_INPLACE_LSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceLshift(x,y)))     \
								     FAIL(err)
#define OP_INPLACE_RSHIFT(x,y,r,err) if (!(r=PyNumber_InPlaceRshift(x,y)))     \
								     FAIL(err)
#define OP_INPLACE_AND(x,y,r,err)    if (!(r=PyNumber_InPlaceAnd(x,y)))        \
								     FAIL(err)
#define OP_INPLACE_OR(x,y,r,err)     if (!(r=PyNumber_InPlaceOr(x,y)))         \
								     FAIL(err)
#define OP_INPLACE_XOR(x,y,r,err)    if (!(r=PyNumber_InPlaceXor(x,y)))        \
								     FAIL(err)

#define OP_GETITEM(x,y,r,err)     if (!(r=PyObject_GetItem1(x,y)))   FAIL(err)
#define OP_SETITEM(x,y,z,r,err)   if ((PyObject_SetItem1(x,y,z))<0)  FAIL(err) \
				  r=Py_None; Py_INCREF(r);
#define OP_DELITEM(x,y,r,err)     if ((PyObject_DelItem(x,y))<0)     FAIL(err) \
				  r=Py_None; Py_INCREF(r);
#define OP_CONTAINS(x,y,r,err)    op_bool(r,err,(PySequence_Contains(x,y)))

#define OP_GETATTR(x,y,r,err)     if (!(r=PyObject_GetAttr(x,y)))    FAIL(err)
#define OP_SETATTR(x,y,z,r,err)   if ((PyObject_SetAttr(x,y,z))<0)   FAIL(err) \
				  r=Py_None; Py_INCREF(r);
#define OP_DELATTR(x,y,r,err)     if ((PyObject_SetAttr(x,y,NULL))<0)FAIL(err) \
				  r=Py_None; Py_INCREF(r);

#define OP_NEWSLICE(x,y,z,r,err)  if (!(r=PySlice_New(x,y,z)))       FAIL(err)

#define OP_GETSLICE(x,y,z,r,err)  {					\
		PyObject *__yo = y, *__zo = z;				\
		int __y = 0, __z = INT_MAX;				\
		if (__yo == Py_None) __yo = NULL;			\
		if (__zo == Py_None) __zo = NULL;			\
		if (!_PyEval_SliceIndex(__yo, &__y) ||			\
		    !_PyEval_SliceIndex(__zo, &__z) ||			\
		    !(r=PySequence_GetSlice(x, __y, __z))) FAIL(err)	\
	}

#define OP_ALLOC_AND_SET(x,y,r,err) { \
		/* XXX check for long/int overflow */ \
		int __i, __x = PyInt_AsLong(x); \
		if (PyErr_Occurred()) FAIL(err) \
		if (!(r = PyList_New(__x))) FAIL(err) \
		for (__i=0; __i<__x; __i++) { \
			Py_INCREF(y); \
			PyList_SET_ITEM(r, __i, y); \
		} \
	}

#define OP_ITER(x,r,err)          if (!(r=PyObject_GetIter(x)))      FAIL(err)
#define OP_NEXT(x,r,err)          if (!(r=PyIter_Next(x))) {                   \
		if (!PyErr_Occurred()) PyErr_SetNone(PyExc_StopIteration);     \
		FAIL(err)                                                      \
	}

#define OP_SIMPLE_CALL(args,r,err) if (!(r=PyObject_CallFunctionObjArgs args)) \
					FAIL(err)
#define OP_CALL_ARGS(args,r,err)   if (!(r=CallWithShape args))    FAIL(err)

/* Needs to act like getattr(x, '__class__', type(x)) */
#define OP_TYPE(x,r,err) { \
		PyObject *o = x; \
		if (PyInstance_Check(o)) { \
			r = (PyObject*)(((PyInstanceObject*)o)->in_class); \
		} else { \
			r = (PyObject*)o->ob_type; \
		} \
		Py_INCREF(r); \
	}

/* Needs to act like instance(x,y) */
#define OP_ISSUBTYPE(x,y,r,err)  \
		op_bool(r,err,PyClass_IsSubclass(x, y))

/*** tests ***/

#define EQ_False(o)     (o == Py_False)
#define EQ_True(o)      (o == Py_True)
#define EQ_0(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==0)
#define EQ_1(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==1)


/*** misc ***/

#define MOVE(x, y)             y = x;

#define INITCHK(expr)          if (!(expr)) return;
#define REGISTER_GLOBAL(name)  Py_INCREF(name); PyModule_AddObject(m, #name, name);


#if defined(USE_CALL_TRACE)

#define TRACE_CALL       __f, __tstate,
#define TRACE_ARGS       PyFrameObject *__f, PyThreadState *__tstate,
#define TRACE_CALL_VOID  __f, __tstate
#define TRACE_ARGS_VOID  PyFrameObject *__f, PyThreadState *__tstate

#define FAIL(err) { __f->f_lineno = __f->f_code->co_firstlineno = __LINE__; goto err; }

#define FUNCTION_HEAD(signature, self, args, names, file, line) \
	PyThreadState *__tstate = PyThreadState_GET(); \
	PyObject *__localnames = PyList_CrazyStringPack names; \
	PyFrameObject *__f = traced_function_head(self, args, signature, file, line, __tstate, __localnames);

#define FUNCTION_CHECK() \
	assert (__f != NULL);

#define ERR_DECREF(arg) { if (__f->f_locals) { PyDict_SetItemString(__f->f_locals, #arg, arg); } Py_DECREF(arg); }

#define FUNCTION_RETURN(rval) return traced_function_tail(rval, __f, __tstate);

#else /* !defined(USE_CALL_TRACE) */

#define TRACE_CALL       /* nothing */
#define TRACE_ARGS       /* nothing */
#define TRACE_CALL_VOID  /* nothing */
#define TRACE_ARGS_VOID  void

#define FAIL(err) { goto err; }

#define FUNCTION_HEAD(signature, self, args, names, file, line)

#define ERR_DECREF(arg) { Py_DECREF(arg); }

#define FUNCTION_CHECK()

#define FUNCTION_RETURN(rval) return rval;

#endif /* defined(USE_CALL_TRACE) */





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
	static PyMethodDef no_methods[] = { (char *)NULL, (PyCFunction)NULL }; \
	PyMODINIT_FUNC init##modname(void)

#define SETUP_MODULE(modname)					\
	PyObject *m = Py_InitModule(#modname, no_methods); \
	PyModule_AddStringConstant(m, "__sourcefile__", __FILE__); \
	this_module_globals = PyModule_GetDict(m); \
	PyGenCFunction_Type.tp_base = &PyCFunction_Type;	\
	PyType_Ready(&PyGenCFunction_Type);	\
	if (setup_globalfunctions(globalfunctiondefs) < 0) \
		return;	\
	if (setup_initcode(frozen_initcode, sizeof(frozen_initcode)) < 0) \
		return;	\
	if (setup_globalobjects(globalobjectdefs) < 0) \
		return;


/*** table of global objects ***/

typedef struct {
	PyObject** p;
	char* name;
} globalobjectdef_t;

typedef struct {
	PyObject** p;
	PyMethodDef ml;
} globalfunctiondef_t;

static int setup_globalobjects(globalobjectdef_t* def)
{
	PyObject* obj;
	
	for (; def->p != NULL; def++) {
		obj = PyDict_GetItemString(this_module_globals, def->name);
		if (obj == NULL) {
			PyErr_Format(PyExc_AttributeError,
				     "initialization code should have "
				     "created '%s'", def->name);
			return -1;
		}
		Py_INCREF(obj);
		*def->p = obj;   /* store the object ref in the global var */
	}
	return 0;
}

static int setup_globalfunctions(globalfunctiondef_t* def)
{
	PyObject* fn;
	PyObject* name;
	int len;

	for (; def->p != NULL; def++) {
		fn = PyCFunction_New(&def->ml, NULL);
		if (fn == NULL)
			return -1;
		fn->ob_type = &PyGenCFunction_Type;
		*def->p = fn;   /* store the object ref in the global var */

		len = 0;
		while (def->ml.ml_name[len] != 0)
			len++;
		name = PyString_FromStringAndSize(NULL, 6+len);
		if (name == NULL)
			return -1;
		memcpy(PyString_AS_STRING(name), "gfunc_", 6);
		memcpy(PyString_AS_STRING(name)+6, def->ml.ml_name, len);
		if (PyDict_SetItem(this_module_globals, name, fn) < 0)
			return -1;
		Py_DECREF(name);
	}
	return 0;
}

static int setup_initcode(char* frozendata, int len)
{
	PyObject* co;
	PyObject* globals;
	PyObject* res;
	co = PyMarshal_ReadObjectFromString(frozendata, len);
	if (co == NULL)
		return -1;
	if (!PyCode_Check(co)) {
		PyErr_SetString(PyExc_TypeError, "uh?");
		return -1;
	}
	globals = this_module_globals;
	if (PyDict_GetItemString(globals, "__builtins__") == NULL)
		PyDict_SetItemString(globals, "__builtins__",
				     PyEval_GetBuiltins());
	res = PyEval_EvalCode((PyCodeObject *) co, globals, globals);
	if (res == NULL)
		return -1;
	Py_DECREF(res);
	return 0;
}


/*** operations with a variable number of arguments ***/

#define OP_NEWLIST0(r,err)         if (!(r=PyList_New(0))) FAIL(err)
#define OP_NEWLIST(args,r,err)     if (!(r=PyList_Pack args)) FAIL(err)
#define OP_NEWDICT0(r,err)         if (!(r=PyDict_New())) FAIL(err)
#define OP_NEWDICT(args,r,err)     if (!(r=PyDict_Pack args)) FAIL(err)
#define OP_NEWTUPLE(args,r,err)    if (!(r=PyTuple_Pack args)) FAIL(err)

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

static PyObject* PyDict_Pack(int n, ...)
{
	int i;
	PyObject *key, *val;
	PyObject *result;
	va_list vargs;

	va_start(vargs, n);
	result = PyDict_New();
	if (result == NULL) {
		return NULL;
	}
	for (i = 0; i < n; i++) {
		key = va_arg(vargs, PyObject *);
		val = va_arg(vargs, PyObject *);
		if (PyDict_SetItem(result, key, val) < 0) {
			Py_DECREF(result);
			return NULL;
		}
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

static PyObject* CallWithShape(PyObject* callable, PyObject* shape, ...)
{
	/* XXX the 'shape' argument is a tuple as specified by
	   XXX pypy.interpreter.argument.fromshape().  This code should
	   XXX we made independent on the format of the 'shape' later... */
	PyObject* result = NULL;
	PyObject* t = NULL;
	PyObject* d = NULL;
	PyObject* o;
	PyObject* key;
	PyObject* t2;
	int i, nargs, nkwds, nvarargs, starflag, starstarflag;
	va_list vargs;

	if (!PyTuple_Check(shape) ||
	    PyTuple_GET_SIZE(shape) != 4 ||
	    !PyInt_Check(PyTuple_GET_ITEM(shape, 0)) ||
	    !PyTuple_Check(PyTuple_GET_ITEM(shape, 1)) ||
	    !PyInt_Check(PyTuple_GET_ITEM(shape, 2)) ||
	    !PyInt_Check(PyTuple_GET_ITEM(shape, 3))) {
		Py_FatalError("in genc.h: invalid 'shape' argument");
	}
	nargs = PyInt_AS_LONG(PyTuple_GET_ITEM(shape, 0));
	nkwds = PyTuple_GET_SIZE(PyTuple_GET_ITEM(shape, 1));
	starflag = PyInt_AS_LONG(PyTuple_GET_ITEM(shape, 2));
	starstarflag = PyInt_AS_LONG(PyTuple_GET_ITEM(shape, 3));

	va_start(vargs, shape);
	t = PyTuple_New(nargs);
	if (t == NULL)
		goto finally;
	for (i = 0; i < nargs; i++) {
		o = va_arg(vargs, PyObject *);
		Py_INCREF(o);
		PyTuple_SET_ITEM(t, i, o);
	}
	if (nkwds) {
		d = PyDict_New();
		if (d == NULL)
			goto finally;
		for (i = 0; i < nkwds; i++) {
			o = va_arg(vargs, PyObject *);
			key = PyTuple_GET_ITEM(PyTuple_GET_ITEM(shape, 1), i);
			if (PyDict_SetItem(d, key, o) < 0)
				goto finally;
		}
	}
	if (starflag) {
		o = va_arg(vargs, PyObject *);
		o = PySequence_Tuple(o);
		if (o == NULL)
			goto finally;
		t2 = PySequence_Concat(t, o);
		Py_DECREF(o);
		Py_DECREF(t);
		t = t2;
		if (t == NULL)
			goto finally;
	}
	if (starstarflag) {
		int len1, len2, len3;
		o = va_arg(vargs, PyObject *);
		len1 = PyDict_Size(d);
		len2 = PyDict_Size(o);
		if (len1 < 0 || len2 < 0)
			goto finally;
		if (PyDict_Update(d, o) < 0)
			goto finally;
		len3 = PyDict_Size(d);
		if (len1 + len2 != len3) {
			PyErr_SetString(PyExc_TypeError,
					"genc.h: duplicate keyword arguments");
			goto finally;
		}
	}
	va_end(vargs);

	result = PyObject_Call(callable, t, d);

 finally:
	Py_XDECREF(d);
	Py_XDECREF(t);
	return result;
}


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
