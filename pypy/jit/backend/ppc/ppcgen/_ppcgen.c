#include <Python.h>
#include <sys/mman.h>

#define __dcbf(base, index)     \
        __asm__ ("dcbf %0, %1" : /*no result*/ : "b%" (index), "r" (base) : "memory")


static PyTypeObject* mmap_type;

#if defined(__APPLE__)

#include <mach-o/dyld.h>

static PyObject*
_ppy_NSLookupAndBindSymbol(PyObject* self, PyObject* args)
{
	char *s;
	NSSymbol sym;

	if (!PyArg_ParseTuple(args, "s", &s))
		return NULL;

	if (!NSIsSymbolNameDefined(s)) {
		return PyErr_Format(PyExc_ValueError,
				    "symbol '%s' not found", s);
	}
		
	sym = NSLookupAndBindSymbol(s);
	
	return PyInt_FromLong((long)NSAddressOfSymbol(sym));
}


#elif defined(linux)

#include <dlfcn.h>

static PyObject*
_ppy_dlsym(PyObject* self, PyObject* args)
{
	char *s;
	void *handle;
	void *sym;

	if (!PyArg_ParseTuple(args, "s", &s))
		return NULL;

	handle = dlopen(RTLD_DEFAULT, RTLD_LAZY);
	sym = dlsym(handle, s);
	if (sym == NULL) {
		return PyErr_Format(PyExc_ValueError,
				    "symbol '%s' not found", s);
	}
	return PyInt_FromLong((long)sym);
}

#else

#error "OS not supported"

#endif


static PyObject*
_ppy_mmap_exec(PyObject* self, PyObject* args)
{
	PyObject* code_args;
	PyObject* r;
	PyObject* mmap_obj;
	char* code;
	size_t size;

	if (!PyArg_ParseTuple(args, "O!O!:mmap_exec",
			      mmap_type, &mmap_obj, 
			      &PyTuple_Type, &code_args)) 
		return NULL;

	code = *((char**)mmap_obj + 2);
	size = *((size_t*)mmap_obj + 3);

	r = ((PyCFunction)code)(NULL, code_args);

	Py_DECREF(args);

	return r;
}

static PyObject*
_ppy_mmap_flush(PyObject* self, PyObject* arg)
{
	char* code;
	size_t size;
	int i = 0;

	if (!PyObject_TypeCheck(arg, mmap_type)) {
		PyErr_SetString(PyExc_TypeError,
			"mmap_flush: single argument must be mmap object");
	}

	code = *((char**)arg + 2);
	size = *((size_t*)arg + 3);

	for (; i < size; i += 32){
		__dcbf(code, i);
	}

	Py_INCREF(Py_None);
	return Py_None;
}


PyMethodDef _ppy_methods[] = {
#if defined(__APPLE__)
	{"NSLookupAndBindSymbol", _ppy_NSLookupAndBindSymbol, 
	 METH_VARARGS, ""},
#elif defined(linux)
	{"dlsym", _ppy_dlsym, METH_VARARGS, ""},
#endif
	{"mmap_exec", _ppy_mmap_exec, METH_VARARGS, ""},
	{"mmap_flush", _ppy_mmap_flush, METH_O, ""},
	{0, 0}
};

#if !defined(MAP_ANON) && defined(__APPLE__)
#define MAP_ANON 0x1000
#endif

PyMODINIT_FUNC
init_ppcgen(void)
{
    PyObject* m;
    PyObject* mmap_module;
    PyObject* mmap_func;
    PyObject* mmap_obj;

    m =	Py_InitModule("_ppcgen", _ppy_methods);

    /* argh */
    /* time to campaign for a C API for the mmap module! */
    mmap_module = PyImport_ImportModule("mmap");
    if (!mmap_module)
	    return;
    mmap_func = PyObject_GetAttrString(mmap_module, "mmap");
    if (!mmap_func)
	    return;
    mmap_obj = PyEval_CallFunction(mmap_func, "iii", -1, 0, MAP_ANON);
    if (!mmap_obj)
	    return;
    mmap_type = mmap_obj->ob_type;
    Py_INCREF(mmap_type);
    Py_DECREF(mmap_obj);
    Py_DECREF(mmap_func);
    Py_DECREF(mmap_module);
}
