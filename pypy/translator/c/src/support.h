
/************************************************************/
 /***  C header subsection: support functions              ***/


/*** misc ***/

#if !defined(MIN)
#define MIN(a,b) (((a)<(b))?(a):(b))
#endif /* MIN */

#define RUNNING_ON_LLINTERP	0

#define FAIL_EXCEPTION(exc, msg) \
	{ \
		RPyRaiseSimpleException(exc, msg); \
	}
#define FAIL_OVF(msg) FAIL_EXCEPTION(PyExc_OverflowError, msg)
#define FAIL_VAL(msg) FAIL_EXCEPTION(PyExc_ValueError, msg)
#define FAIL_ZER(msg) FAIL_EXCEPTION(PyExc_ZeroDivisionError, msg)
#define CFAIL()       RPyConvertExceptionFromCPython()

/* the following macros are used by rpython/lltypesystem/rstr.py */
#define PyString_FromRPyString(rpystr) \
	PyString_FromStringAndSize(_RPyString_AsString(rpystr), RPyString_Size(rpystr))

#define PyUnicode_FromRPyUnicode(rpystr) \
	PyUnicode_FromUnicode(_RPyUnicode_AsUnicode(rpystr), RPyUnicode_Size(rpystr))

#define PyString_ToRPyString(s, rpystr)                            \
	memcpy(_RPyString_AsString(rpystr), PyString_AS_STRING(s), \
		RPyString_Size(rpystr))

/* Extra checks can be enabled with the RPY_ASSERT or RPY_LL_ASSERT
 * macros.  They differ in the level at which the tests are made.
 * Remember that RPython lists, for example, are implemented as a
 * GcStruct pointing to an over-allocated GcArray.  With RPY_ASSERT you
 * get list index out of bound checks from rlist.py; such tests must be
 * manually written so made we've forgotten a case.  Conversely, with
 * RPY_LL_ASSERT, all GcArray indexing are checked, which is safer
 * against attacks and segfaults - but less precise in the case of
 * lists, because of the overallocated bit.
 *
 * For extra safety, in programs translated with --sandbox we always
 * assume that we want RPY_LL_ASSERT.  You can change it below to trade
 * safety for performance, though the hit is not huge (~10%?).
 */
#ifdef RPY_ASSERT
#  define RPyAssert(x, msg)                                             \
     if (!(x)) RPyAssertFailed(__FILE__, __LINE__, __FUNCTION__, msg)

void RPyAssertFailed(const char* filename, long lineno,
                     const char* function, const char *msg);
#  ifndef PYPY_NOT_MAIN_FILE
void RPyAssertFailed(const char* filename, long lineno,
                     const char* function, const char *msg) {
  fprintf(stderr,
          "PyPy assertion failed at %s:%ld:\n"
          "in %s: %s\n",
          filename, lineno, function, msg);
  abort();
}
#  endif
#else
#  define RPyAssert(x, msg)   /* nothing */
#endif

#if defined(RPY_LL_ASSERT) || defined(RPY_SANDBOXED)
/* obscure macros that can be used as expressions and lvalues to refer
 * to a field of a structure or an item in an array in a "safe" way --
 * they abort() in case of null pointer or out-of-bounds index.  As a
 * speed trade-off, RPyItem actually segfaults if the array is null, but
 * it's a "guaranteed" segfault and not one that can be used by
 * attackers.
 */
#  define RPyCHECK(x)           ((x) || RPyAbort())
#  define RPyField(ptr, name)   ((RPyCHECK(ptr), (ptr))->name)
#  define RPyItem(array, index)                                             \
     ((RPyCHECK((index) >= 0 && (index) < (array)->length),                 \
      (array))->items[index])
#  define RPyFxItem(ptr, index, fixedsize)                                  \
     ((RPyCHECK((ptr) && (index) >= 0 && (index) < (fixedsize)),            \
      (ptr))[index])
#  define RPyNLenItem(array, index)                                         \
     ((RPyCHECK((array) && (index) >= 0), (array))->items[index])
#  define RPyBareItem(array, index)                                         \
     ((RPyCHECK((array) && (index) >= 0), (array))[index])

int RPyAbort(void);
#ifndef PYPY_NOT_MAIN_FILE
int RPyAbort(void) {
  fprintf(stderr, "Invalid RPython operation (NULL ptr or bad array index)\n");
  abort();
  return 0;
}
#endif

#else
#  define RPyField(ptr, name)                ((ptr)->name)
#  define RPyItem(array, index)              ((array)->items[index])
#  define RPyFxItem(ptr, index, fixedsize)   ((ptr)[index])
#  define RPyNLenItem(array, index)          ((array)->items[index])
#  define RPyBareItem(array, index)          ((array)[index])
#endif

#ifndef PYPY_STANDALONE

/* prototypes */

PyObject * gencfunc_descr_get(PyObject *func, PyObject *obj, PyObject *type);
PyObject* PyList_Pack(int n, ...);
PyObject* PyDict_Pack(int n, ...);
#if PY_VERSION_HEX < 0x02040000   /* 2.4 */
PyObject* PyTuple_Pack(int n, ...);
#endif
#if PY_VERSION_HEX >= 0x02030000   /* 2.3 */
# define PyObject_GetItem1  PyObject_GetItem
# define PyObject_SetItem1  PyObject_SetItem
#else
PyObject* PyObject_GetItem1(PyObject* obj, PyObject* index);
PyObject* PyObject_SetItem1(PyObject* obj, PyObject* index, PyObject* v);
#endif
PyObject* CallWithShape(PyObject* callable, PyObject* shape, ...);
PyObject* decode_arg(PyObject* fname, int position, PyObject* name,
			    PyObject* vargs, PyObject* vkwds, PyObject* def);
int check_no_more_arg(PyObject* fname, int n, PyObject* vargs);
int check_self_nonzero(PyObject* fname, PyObject* self);
PyObject *PyTuple_GetItem_WithIncref(PyObject *tuple, int index);
int PyTuple_SetItem_WithIncref(PyObject *tuple, int index, PyObject *o);
int PySequence_Contains_with_exc(PyObject *seq, PyObject *ob);

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

/* we need a subclass of 'builtin_function_or_method' which can be used
   as methods: builtin function objects that can be bound on instances */
PyObject *
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


/*** misc support functions ***/

PyObject* PyList_Pack(int n, ...)
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

PyObject* PyDict_Pack(int n, ...)
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
PyObject* PyTuple_Pack(int n, ...)
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

#if PY_VERSION_HEX < 0x02030000   /* 2.3 */
/* for Python 2.2 only */
PyObject* PyObject_GetItem1(PyObject* obj, PyObject* index)
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

PyObject* PyObject_SetItem1(PyObject* obj, PyObject* index, PyObject* v)
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

PyObject* CallWithShape(PyObject* callable, PyObject* shape, ...)
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
	int i, nargs, nkwds, starflag, starstarflag;
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

PyObject* decode_arg(PyObject* fname, int position, PyObject* name,
			    PyObject* vargs, PyObject* vkwds, PyObject* def)
{
	PyObject* result;
	int size = PyTuple_Size(vargs);
	if (size < 0)
		return NULL;
	if (vkwds != NULL) {
		result = PyDict_GetItem(vkwds, name);
		if (result != NULL) {
			if (position < size) {
				PyErr_Format(PyExc_TypeError,
					     "%s() got duplicate value for "
					     "its '%s' argument",
					     PyString_AS_STRING(fname),
					     PyString_AS_STRING(name));
				return NULL;
			}
			Py_INCREF(result);
			return result;
		}
	}
	if (position < size) {
		/* common case */
		result = PyTuple_GET_ITEM(vargs, position);
		Py_INCREF(result);
		return result;
	}
	if (def != NULL) {
		Py_INCREF(def);
		return def;
	}
	PyErr_Format(PyExc_TypeError, "%s() got only %d argument(s)",
		     PyString_AS_STRING(fname),
		     position);
	return NULL;
}

int check_no_more_arg(PyObject* fname, int n, PyObject* vargs)
{
	int size = PyTuple_Size(vargs);
	if (size < 0)
		return -1;
	if (size > n) {
		PyErr_Format(PyExc_TypeError,
			     "%s() got %d argument(s), expected %d",
			     PyString_AS_STRING(fname),
			     size, n);
		return -1;
	}
	return 0;
}

int check_self_nonzero(PyObject* fname, PyObject* self)
{
	if (!self) {
		    PyErr_Format(PyExc_TypeError,
				"%s() expects instance first arg",
				PyString_AS_STRING(fname));
		    return -1;
	}
	return 0;
}
		
/************************************************************/

PyObject *PyTuple_GetItem_WithIncref(PyObject *tuple, int index)
{
	PyObject *result = PyTuple_GetItem(tuple, index);
	Py_XINCREF(result);
	return result;
}

int PyTuple_SetItem_WithIncref(PyObject *tuple, int index, PyObject *o)
{
	Py_INCREF(o);
	return PyTuple_SetItem(tuple, index, o);
}

int PySequence_Contains_with_exc(PyObject *seq, PyObject *ob)
{
	int ret = PySequence_Contains(seq, ob);
	
	if (ret < 0) 
		CFAIL();
	return ret;
}

#endif /* PYPY_STANDALONE */

#endif /* PYPY_NOT_MAIN_FILE */
