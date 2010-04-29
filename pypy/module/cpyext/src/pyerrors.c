#include <Python.h>
#include <string.h>

PyObject *
PyErr_Format(PyObject *exception, const char *format, ...)
{
	va_list vargs;
	PyObject* string;

#ifdef HAVE_STDARG_PROTOTYPES
	va_start(vargs, format);
#else
  va_start(vargs);
#endif

	string = PyString_FromFormatV(format, vargs);
	PyErr_SetObject(exception, string);
	Py_XDECREF(string);
	va_end(vargs);
	return NULL;
}

PyObject *
PyErr_NewException(char *name, PyObject *base, PyObject *dict)
{
	char *dot;
	PyObject *modulename = NULL;
	PyObject *classname = NULL;
	PyObject *mydict = NULL;
	PyObject *bases = NULL;
	PyObject *result = NULL;
	dot = strrchr(name, '.');
	if (dot == NULL) {
		PyErr_SetString(PyExc_SystemError,
			"PyErr_NewException: name must be module.class");
		return NULL;
	}
	if (base == NULL)
		base = PyExc_Exception;
	if (dict == NULL) {
		dict = mydict = PyDict_New();
		if (dict == NULL)
			goto failure;
	}
	if (PyDict_GetItemString(dict, "__module__") == NULL) {
		modulename = PyString_FromStringAndSize(name,
						     (Py_ssize_t)(dot-name));
		if (modulename == NULL)
			goto failure;
		if (PyDict_SetItemString(dict, "__module__", modulename) != 0)
			goto failure;
	}
	if (PyTuple_Check(base)) {
		bases = base;
		/* INCREF as we create a new ref in the else branch */
		Py_INCREF(bases);
	} else {
		bases = PyTuple_Pack(1, base);
		if (bases == NULL)
			goto failure;
	}
	/* Create a real new-style class. */
	result = PyObject_CallFunction((PyObject *)&PyType_Type, "sOO",
				       dot+1, bases, dict);
  failure:
	Py_XDECREF(bases);
	Py_XDECREF(mydict);
	Py_XDECREF(classname);
	Py_XDECREF(modulename);
	return result;
}
