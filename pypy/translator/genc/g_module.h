
/************************************************************/
 /***  C header subsection: CPython-extension-module-ness  ***/


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
	if (setup_initcode(frozen_initcode, FROZEN_INITCODE_SIZE) < 0) \
		return;	\
	if (setup_globalobjects(globalobjectdefs) < 0) \
		return;


/*** table of global objects ***/

static PyObject *this_module_globals;

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

static int setup_initcode(char* frozendata[], int len)
{
	PyObject* co;
	PyObject* globals;
	PyObject* res;
	char *buffer, *bufp;
	int chunk, count = 0;
	
	buffer = PyMem_NEW(char, len);
	if (buffer == NULL)
		return -1;
	bufp = buffer;
	while (count < len) {
		chunk = len-count < 1024 ? len-count : 1024;
		memcpy(bufp, *frozendata, chunk);
		bufp += chunk;
		count += chunk;
		++frozendata;
	}
	co = PyMarshal_ReadObjectFromString(buffer, len);
	if (co == NULL)
		return -1;
	PyMem_DEL(buffer);
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
