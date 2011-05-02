
/* Module support implementation */

#include "Python.h"

#define FLAG_SIZE_T 1
typedef double va_double;

static PyObject *va_build_value(const char *, va_list, int);

/* Package context -- the full module name for package imports */
char *_Py_PackageContext = NULL;

/* Py_InitModule4() parameters:
   - name is the module name
   - methods is the list of top-level functions
   - doc is the documentation string
   - passthrough is passed as self to functions defined in the module
   - api_version is the value of PYTHON_API_VERSION at the time the
     module was compiled

   Return value is a borrowed reference to the module object; or NULL
   if an error occurred (in Python 1.4 and before, errors were fatal).
   Errors may still leak memory.
*/

static char api_version_warning[] =
"Python C API version mismatch for module %.100s:\
 This Python has API version %d, module %.100s has version %d.";

/* Helper for mkvalue() to scan the length of a format */

static int
countformat(const char *format, int endchar)
{
	int count = 0;
	int level = 0;
	while (level > 0 || *format != endchar) {
		switch (*format) {
		case '\0':
			/* Premature end */
			PyErr_SetString(PyExc_SystemError,
					"unmatched paren in format");
			return -1;
		case '(':
		case '[':
		case '{':
			if (level == 0)
				count++;
			level++;
			break;
		case ')':
		case ']':
		case '}':
			level--;
			break;
		case '#':
		case '&':
		case ',':
		case ':':
		case ' ':
		case '\t':
			break;
		default:
			if (level == 0)
				count++;
		}
		format++;
	}
	return count;
}


/* Generic function to create a value -- the inverse of getargs() */
/* After an original idea and first implementation by Steven Miale */

static PyObject *do_mktuple(const char**, va_list *, int, int, int);
static PyObject *do_mklist(const char**, va_list *, int, int, int);
static PyObject *do_mkdict(const char**, va_list *, int, int, int);
static PyObject *do_mkvalue(const char**, va_list *, int);


static PyObject *
do_mkdict(const char **p_format, va_list *p_va, int endchar, int n, int flags)
{
	PyObject *d;
	int i;
	int itemfailed = 0;
	if (n < 0)
		return NULL;
	if ((d = PyDict_New()) == NULL)
		return NULL;
	/* Note that we can't bail immediately on error as this will leak
	   refcounts on any 'N' arguments. */
	for (i = 0; i < n; i+= 2) {
		PyObject *k, *v;
		int err;
		k = do_mkvalue(p_format, p_va, flags);
		if (k == NULL) {
			itemfailed = 1;
			Py_INCREF(Py_None);
			k = Py_None;
		}
		v = do_mkvalue(p_format, p_va, flags);
		if (v == NULL) {
			itemfailed = 1;
			Py_INCREF(Py_None);
			v = Py_None;
		}
		err = PyDict_SetItem(d, k, v);
		Py_DECREF(k);
		Py_DECREF(v);
		if (err < 0 || itemfailed) {
			Py_DECREF(d);
			return NULL;
		}
	}
	if (d != NULL && **p_format != endchar) {
		Py_DECREF(d);
		d = NULL;
		PyErr_SetString(PyExc_SystemError,
				"Unmatched paren in format");
	}
	else if (endchar)
		++*p_format;
	return d;
}

static PyObject *
do_mklist(const char **p_format, va_list *p_va, int endchar, int n, int flags)
{
	PyObject *v;
	int i;
	int itemfailed = 0;
	if (n < 0)
		return NULL;
	v = PyList_New(n);
	if (v == NULL)
		return NULL;
	/* Note that we can't bail immediately on error as this will leak
	   refcounts on any 'N' arguments. */
	for (i = 0; i < n; i++) {
		PyObject *w = do_mkvalue(p_format, p_va, flags);
		if (w == NULL) {
			itemfailed = 1;
			Py_INCREF(Py_None);
			w = Py_None;
		}
		PyList_SET_ITEM(v, i, w);
	}

	if (itemfailed) {
		/* do_mkvalue() should have already set an error */
		Py_DECREF(v);
		return NULL;
	}
	if (**p_format != endchar) {
		Py_DECREF(v);
		PyErr_SetString(PyExc_SystemError,
				"Unmatched paren in format");
		return NULL;
	}
	if (endchar)
		++*p_format;
	return v;
}

#ifdef Py_USING_UNICODE
static int
_ustrlen(Py_UNICODE *u)
{
	int i = 0;
	Py_UNICODE *v = u;
	while (*v != 0) { i++; v++; } 
	return i;
}
#endif

static PyObject *
do_mktuple(const char **p_format, va_list *p_va, int endchar, int n, int flags)
{
	PyObject *v;
	int i;
	int itemfailed = 0;
	if (n < 0)
		return NULL;
	if ((v = PyTuple_New(n)) == NULL)
		return NULL;
	/* Note that we can't bail immediately on error as this will leak
	   refcounts on any 'N' arguments. */
	for (i = 0; i < n; i++) {
		PyObject *w = do_mkvalue(p_format, p_va, flags);
		if (w == NULL) {
			itemfailed = 1;
			Py_INCREF(Py_None);
			w = Py_None;
		}
		PyTuple_SET_ITEM(v, i, w);
	}
	if (itemfailed) {
		/* do_mkvalue() should have already set an error */
		Py_DECREF(v);
		return NULL;
	}
	if (**p_format != endchar) {
		Py_DECREF(v);
		PyErr_SetString(PyExc_SystemError,
				"Unmatched paren in format");
		return NULL;
	}
	if (endchar)
		++*p_format;
	return v;
}

static PyObject *
do_mkvalue(const char **p_format, va_list *p_va, int flags)
{
	for (;;) {
		switch (*(*p_format)++) {
		case '(':
			return do_mktuple(p_format, p_va, ')',
					  countformat(*p_format, ')'), flags);

		case '[':
			return do_mklist(p_format, p_va, ']',
					 countformat(*p_format, ']'), flags);

		case '{':
			return do_mkdict(p_format, p_va, '}',
					 countformat(*p_format, '}'), flags);

		case 'b':
		case 'B':
		case 'h':
		case 'i':
			return PyInt_FromLong((long)va_arg(*p_va, int));
			
		case 'H':
			return PyInt_FromLong((long)va_arg(*p_va, unsigned int));

		case 'I':
		{
			unsigned int n;
			n = va_arg(*p_va, unsigned int);
			if (n > (unsigned long)PyInt_GetMax())
				return PyLong_FromUnsignedLong((unsigned long)n);
			else
				return PyInt_FromLong(n);
		}
		
		case 'n':
#if SIZEOF_SIZE_T!=SIZEOF_LONG
			return PyInt_FromSsize_t(va_arg(*p_va, Py_ssize_t));
#endif
			/* Fall through from 'n' to 'l' if Py_ssize_t is long */
		case 'l':
			return PyInt_FromLong(va_arg(*p_va, long));

		case 'k':
		{
			unsigned long n;
			n = va_arg(*p_va, unsigned long);
			if (n > (unsigned long)PyInt_GetMax())
				return PyLong_FromUnsignedLong(n);
			else
				return PyInt_FromLong(n);
		}

#ifdef HAVE_LONG_LONG
		case 'L':
			return PyLong_FromLongLong((PY_LONG_LONG)va_arg(*p_va, PY_LONG_LONG));

		case 'K':
			return PyLong_FromUnsignedLongLong((PY_LONG_LONG)va_arg(*p_va, unsigned PY_LONG_LONG));
#endif
#ifdef Py_USING_UNICODE
		case 'u':
		{
			PyObject *v;
			Py_UNICODE *u = va_arg(*p_va, Py_UNICODE *);
			Py_ssize_t n;	
			if (**p_format == '#') {
				++*p_format;
				if (flags & FLAG_SIZE_T)
					n = va_arg(*p_va, Py_ssize_t);
				else
					n = va_arg(*p_va, int);
			}
			else
				n = -1;
			if (u == NULL) {
				v = Py_None;
				Py_INCREF(v);
			}
			else {
				if (n < 0)
					n = _ustrlen(u);
				v = PyUnicode_FromUnicode(u, n);
			}
			return v;
		}
#endif
		case 'f':
		case 'd':
			return PyFloat_FromDouble(
				(double)va_arg(*p_va, va_double));

#ifndef WITHOUT_COMPLEX
		case 'D':
			return PyComplex_FromCComplex(
				*((Py_complex *)va_arg(*p_va, Py_complex *)));
#endif /* WITHOUT_COMPLEX */

		case 'c':
		{
			char p[1];
			p[0] = (char)va_arg(*p_va, int);
			return PyString_FromStringAndSize(p, 1);
		}

		case 's':
		case 'z':
		{
			PyObject *v;
			char *str = va_arg(*p_va, char *);
			Py_ssize_t n;
			if (**p_format == '#') {
				++*p_format;
				if (flags & FLAG_SIZE_T)
					n = va_arg(*p_va, Py_ssize_t);
				else
					n = va_arg(*p_va, int);
			}
			else
				n = -1;
			if (str == NULL) {
				v = Py_None;
				Py_INCREF(v);
			}
			else {
				if (n < 0) {
					size_t m = strlen(str);
					if (m > PY_SSIZE_T_MAX) {
						PyErr_SetString(PyExc_OverflowError,
							"string too long for Python string");
						return NULL;
					}
					n = (Py_ssize_t)m;
				}
				v = PyString_FromStringAndSize(str, n);
			}
			return v;
		}

		case 'N':
		case 'S':
		case 'O':
		if (**p_format == '&') {
			typedef PyObject *(*converter)(void *);
			converter func = va_arg(*p_va, converter);
			void *arg = va_arg(*p_va, void *);
			++*p_format;
			return (*func)(arg);
		}
		else {
			PyObject *v;
			v = va_arg(*p_va, PyObject *);
			if (v != NULL) {
				if (*(*p_format - 1) != 'N')
					Py_INCREF(v);
			}
			else if (!PyErr_Occurred())
				/* If a NULL was passed
				 * because a call that should
				 * have constructed a value
				 * failed, that's OK, and we
				 * pass the error on; but if
				 * no error occurred it's not
				 * clear that the caller knew
				 * what she was doing. */
				PyErr_SetString(PyExc_SystemError,
					"NULL object passed to Py_BuildValue");
			return v;
		}

		case ':':
		case ',':
		case ' ':
		case '\t':
			break;

		default:
			PyErr_SetString(PyExc_SystemError,
				"bad format char passed to Py_BuildValue");
			return NULL;

		}
	}
}


PyObject *
Py_BuildValue(const char *format, ...)
{
	va_list va;
	PyObject* retval;
	va_start(va, format);
	retval = va_build_value(format, va, 0);
	va_end(va);
	return retval;
}

PyObject *
_Py_BuildValue_SizeT(const char *format, ...)
{
	va_list va;
	PyObject* retval;
	va_start(va, format);
	retval = va_build_value(format, va, FLAG_SIZE_T);
	va_end(va);
	return retval;
}

PyObject *
Py_VaBuildValue(const char *format, va_list va)
{
	return va_build_value(format, va, 0);
}

PyObject *
_Py_VaBuildValue_SizeT(const char *format, va_list va)
{
	return va_build_value(format, va, FLAG_SIZE_T);
}

static PyObject *
va_build_value(const char *format, va_list va, int flags)
{
	const char *f = format;
	int n = countformat(f, '\0');
	va_list lva;

#ifdef VA_LIST_IS_ARRAY
	memcpy(lva, va, sizeof(va_list));
#else
#ifdef __va_copy
	__va_copy(lva, va);
#else
	lva = va;
#endif
#endif

	if (n < 0)
		return NULL;
	if (n == 0) {
		Py_INCREF(Py_None);
		return Py_None;
	}
	if (n == 1)
		return do_mkvalue(&f, &lva, flags);
	return do_mktuple(&f, &lva, '\0', n, flags);
}


PyObject *
PyEval_CallFunction(PyObject *obj, const char *format, ...)
{
	va_list vargs;
	PyObject *args;
	PyObject *res;

	va_start(vargs, format);

	args = Py_VaBuildValue(format, vargs);
	va_end(vargs);

	if (args == NULL)
		return NULL;

	res = PyEval_CallObject(obj, args);
	Py_DECREF(args);

	return res;
}


PyObject *
PyEval_CallMethod(PyObject *obj, const char *methodname, const char *format, ...)
{
	va_list vargs;
	PyObject *meth;
	PyObject *args;
	PyObject *res;

	meth = PyObject_GetAttrString(obj, methodname);
	if (meth == NULL)
		return NULL;

	va_start(vargs, format);

	args = Py_VaBuildValue(format, vargs);
	va_end(vargs);

	if (args == NULL) {
		Py_DECREF(meth);
		return NULL;
	}

	res = PyEval_CallObject(meth, args);
	Py_DECREF(meth);
	Py_DECREF(args);

	return res;
}

static PyObject*
call_function_tail(PyObject *callable, PyObject *args)
{
	PyObject *retval;

	if (args == NULL)
		return NULL;

	if (!PyTuple_Check(args)) {
		PyObject *a;

		a = PyTuple_New(1);
		if (a == NULL) {
			Py_DECREF(args);
			return NULL;
		}
		PyTuple_SET_ITEM(a, 0, args);
		args = a;
	}
	retval = PyObject_Call(callable, args, NULL);

	Py_DECREF(args);

	return retval;
}

PyObject *
PyObject_CallFunction(PyObject *callable, char *format, ...)
{
	va_list va;
	PyObject *args;

	if (format && *format) {
		va_start(va, format);
		args = Py_VaBuildValue(format, va);
		va_end(va);
	}
	else
		args = PyTuple_New(0);

	return call_function_tail(callable, args);
}

PyObject *
PyObject_CallMethod(PyObject *o, char *name, char *format, ...)
{
	va_list va;
	PyObject *args;
	PyObject *func = NULL;
	PyObject *retval = NULL;

	func = PyObject_GetAttrString(o, name);
	if (func == NULL) {
		PyErr_SetString(PyExc_AttributeError, name);
		return 0;
	}

	if (format && *format) {
		va_start(va, format);
		args = Py_VaBuildValue(format, va);
		va_end(va);
	}
	else
		args = PyTuple_New(0);

	retval = call_function_tail(func, args);

  exit:
	/* args gets consumed in call_function_tail */
	Py_XDECREF(func);

	return retval;
}

static PyObject *
objargs_mktuple(va_list va)
{
	int i, n = 0;
	va_list countva;
	PyObject *result, *tmp;

#ifdef VA_LIST_IS_ARRAY
	memcpy(countva, va, sizeof(va_list));
#else
#ifdef __va_copy
	__va_copy(countva, va);
#else
	countva = va;
#endif
#endif

	while (((PyObject *)va_arg(countva, PyObject *)) != NULL)
		++n;
	result = PyTuple_New(n);
	if (result != NULL && n > 0) {
		for (i = 0; i < n; ++i) {
			tmp = (PyObject *)va_arg(va, PyObject *);
			PyTuple_SET_ITEM(result, i, tmp);
			Py_INCREF(tmp);
		}
	}
	return result;
}

PyObject *
PyObject_CallFunctionObjArgs(PyObject *callable, ...)
{
	PyObject *args, *tmp;
	va_list vargs;

	/* count the args */
	va_start(vargs, callable);
	args = objargs_mktuple(vargs);
	va_end(vargs);
	if (args == NULL)
		return NULL;
	tmp = PyObject_Call(callable, args, NULL);
	Py_DECREF(args);

	return tmp;
}

PyObject *
PyObject_CallMethodObjArgs(PyObject *callable, PyObject *name, ...)
{
	PyObject *args, *tmp;
	va_list vargs;

	callable = PyObject_GetAttr(callable, name);
	if (callable == NULL)
		return NULL;

	/* count the args */
	va_start(vargs, name);
	args = objargs_mktuple(vargs);
	va_end(vargs);
	if (args == NULL) {
		Py_DECREF(callable);
		return NULL;
	}
	tmp = PyObject_Call(callable, args, NULL);
	Py_DECREF(args);
	Py_DECREF(callable);

	return tmp;
}

/* returns -1 in case of error, 0 if a new key was added, 1 if the key
   was already there (and replaced) */
static int
_PyModule_AddObject_NoConsumeRef(PyObject *m, const char *name, PyObject *o)
{
	PyObject *dict, *prev;
	if (!PyModule_Check(m)) {
		PyErr_SetString(PyExc_TypeError,
			    "PyModule_AddObject() needs module as first arg");
		return -1;
	}
	if (!o) {
		if (!PyErr_Occurred())
			PyErr_SetString(PyExc_TypeError,
					"PyModule_AddObject() needs non-NULL value");
		return -1;
	}

	dict = PyModule_GetDict(m);
	if (dict == NULL) {
		/* Internal error -- modules must have a dict! */
		PyErr_Format(PyExc_SystemError, "module '%s' has no __dict__",
			     PyModule_GetName(m));
		return -1;
	}
	prev = PyDict_GetItemString(dict, name);
	if (PyDict_SetItemString(dict, name, o))
		return -1;
	return prev != NULL;
}

int
PyModule_AddObject(PyObject *m, const char *name, PyObject *o)
{
	int result = _PyModule_AddObject_NoConsumeRef(m, name, o);
	/* XXX WORKAROUND for a common misusage of PyModule_AddObject:
	   for the common case of adding a new key, we don't consume a
	   reference, but instead just leak it away.  The issue is that
	   people generally don't realize that this function consumes a
	   reference, because on CPython the reference is still stored
	   on the dictionary. */
	if (result != 0)
		Py_DECREF(o);
	return result < 0 ? -1 : 0;
}

int 
PyModule_AddIntConstant(PyObject *m, const char *name, long value)
{
	int result;
	PyObject *o = PyInt_FromLong(value);
	if (!o)
		return -1;
	result = _PyModule_AddObject_NoConsumeRef(m, name, o);
	Py_DECREF(o);
	return result < 0 ? -1 : 0;
}

int 
PyModule_AddStringConstant(PyObject *m, const char *name, const char *value)
{
	int result;
	PyObject *o = PyString_FromString(value);
	if (!o)
		return -1;
	result = _PyModule_AddObject_NoConsumeRef(m, name, o);
	Py_DECREF(o);
	return result < 0 ? -1 : 0;
}
