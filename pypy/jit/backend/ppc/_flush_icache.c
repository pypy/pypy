#include <Python.h>
#include "../../../translator/c/src/asm_ppc.h"

static PyObject*
_flush_icache(PyObject *self, PyObject *args)
{
	long base, size;

	if (!PyArg_ParseTuple(args, "ii:_flush_icache", &base, &size))
		return NULL;

	LL_flush_icache(base, size);
	Py_INCREF(Py_None);
	return Py_None;
}

PyMethodDef _flush_icache_methods[] = {
	{"_flush_icache", _flush_icache, METH_VARARGS, ""},
	{0, 0}
};

PyMODINIT_FUNC
init_flush_icache(void)
{
	Py_InitModule("_flush_icache", _flush_icache_methods);
}
