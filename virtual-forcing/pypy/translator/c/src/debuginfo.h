
/************************************************************/
 /***  C header subsection: debugging info                 ***/

/* NOTE: this is not included by <g_include.h>.
   The #include is generated manually if needed. */

#undef METHODDEF_DEBUGINFO
#define METHODDEF_DEBUGINFO						\
		{ "debuginfo_offset", debuginfo_offset, METH_VARARGS },	\
		{ "debuginfo_global", debuginfo_global, METH_VARARGS },	\
		{ "debuginfo_peek",   debuginfo_peek,   METH_VARARGS },

/* prototypes */

PyObject *debuginfo_offset(PyObject *self, PyObject *args);
PyObject *debuginfo_global(PyObject *self, PyObject *args);
PyObject *debuginfo_peek(PyObject *self, PyObject *args);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

PyObject *debuginfo_offset(PyObject *self, PyObject *args)
{
	int index;
	if (!PyArg_ParseTuple(args, "i", &index))
		return NULL;
	return PyInt_FromLong(debuginfo_offsets[index]);
}

PyObject *debuginfo_global(PyObject *self, PyObject *args)
{
	int index;
	if (!PyArg_ParseTuple(args, "i", &index))
		return NULL;
	return PyLong_FromVoidPtr(debuginfo_globals[index]);
}

PyObject *debuginfo_peek(PyObject *self, PyObject *args)
{
	PyObject *o;
	int size;
	void *start;
	if (!PyArg_ParseTuple(args, "Oi", &o, &size))
		return NULL;
	start = PyLong_AsVoidPtr(o);
	if (PyErr_Occurred())
		return NULL;
	return PyString_FromStringAndSize((char *)start, size);
}

#endif /* PYPY_NOT_MAIN_FILE */
