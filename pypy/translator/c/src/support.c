#include "common_header.h"
#include <src/support.h>

/************************************************************/
/***  C header subsection: support functions              ***/

#include <stdio.h>
#include <stdlib.h>

/*** misc ***/

void RPyAssertFailed(const char* filename, long lineno,
                     const char* function, const char *msg) {
  fprintf(stderr,
          "PyPy assertion failed at %s:%ld:\n"
          "in %s: %s\n",
          filename, lineno, function, msg);
  abort();
}

void RPyAbort(void) {
  fprintf(stderr, "Invalid RPython operation (NULL ptr or bad array index)\n");
  abort();
}

#ifdef PYPY_CPYTHON_EXTENSION

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

PyObject* _PyUnicode_FromRPyUnicode(wchar_t *items, long length)
{
    PyObject *u = PyUnicode_FromUnicode(NULL, length);
    long i;
    for (i=0; i<length; i++) {
        /* xxx possibly silently truncate the unichars */
        PyUnicode_AS_UNICODE(u)[i] = items[i];
    }
    return u;
}
#endif  /* PYPY_CPYTHON_EXTENSION */
