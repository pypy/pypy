
/************************************************************/
 /***  C header subsection: CPython-extension-module-ness  ***/

#ifdef COUNT_OP_MALLOCS
# define METHODDEF_MALLOC_COUNTERS	\
		{ "malloc_counters", malloc_counters, METH_VARARGS },
#else
# define METHODDEF_MALLOC_COUNTERS	/* nothing */
#endif

#define METHODDEF_DEBUGINFO    /* nothing, unless overridden by g_debuginfo.h */

#define MODULE_INITFUNC(modname)                        \
	static PyMethodDef my_methods[] = {             \
		METHODDEF_MALLOC_COUNTERS               \
		METHODDEF_DEBUGINFO                     \
		{ (char *)NULL, (PyCFunction)NULL } };  \
	PyMODINIT_FUNC init##modname(void)

#define SETUP_MODULE(modname)	\
	char *errmsg; \
	PyObject *m = Py_InitModule(#modname, my_methods); \
	PyModule_AddStringConstant(m, "__sourcefile__", __FILE__); \
	this_module_globals = PyModule_GetDict(m); \
	PyGenCFunction_Type.tp_base = &PyCFunction_Type;	\
	PyGenCFunction_Type.tp_getset = PyCFunction_Type.tp_getset; \
	PyType_Ready(&PyGenCFunction_Type);	\
	RPythonError = PyErr_NewException(#modname ".RPythonError", \
					  NULL, NULL); \
	if (RPythonError == NULL) \
		return; \
	PyModule_AddObject(m, "RPythonError", RPythonError); \
	errmsg = RPython_StartupCode(); \
	if (errmsg) { \
		PyErr_SetString(PyExc_RuntimeError, errmsg); \
		return; \
	} \
	if (setup_globalfunctions(globalfunctiondefs, #modname) < 0) \
		return;	\
	if (setup_exportglobalobjects(cpyobjheaddefs) < 0)	\
		return;	\
	if (setup_initcode(frozen_initcode, FROZEN_INITCODE_SIZE) < 0) \
		return;	\
	if (setup_globalobjects(globalobjectdefs, cpyobjheaddefs) < 0) \
		return;

/*** table of global objects ***/

static PyObject *this_module_globals;

typedef struct {
	PyObject** p;
	char* name;
} globalobjectdef_t;

typedef struct {
	char* name;
	PyObject* cpyobj;
	void (*setupfn)(PyObject *);
} cpyobjheaddef_t;

typedef struct {
	PyObject** p;
	char* gfunc_name;
	PyMethodDef ml;
} globalfunctiondef_t;

/* helper-hook for post-setup */
static globalfunctiondef_t *globalfunctiondefsptr;
static PyObject *postsetup_get_typedict(PyObject *tp);
static PyObject *postsetup_get_methodname(int funcidx);
static PyObject *postsetup_build_method(int funcidx, PyObject *type);
int call_postsetup(PyObject *m);

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

static int setup_exportglobalobjects(cpyobjheaddef_t* cpyheadtable)
{
	PyObject* obj;
	cpyobjheaddef_t* cpydef;

	/* Store the object given by their heads into the module's dict.
	   Warning: these object heads might still be invalid, e.g.
	   typically their ob_type needs patching!
	   But PyDict_SetItemString() doesn't inspect them...
	*/
	for (cpydef = cpyheadtable; cpydef->name != NULL; cpydef++) {
		obj = cpydef->cpyobj;
		if (PyDict_SetItemString(this_module_globals,
					 cpydef->name, obj) < 0)
			return -1;
	}
	return 0;
}

static int setup_globalobjects(globalobjectdef_t* globtable,
			       cpyobjheaddef_t* cpyheadtable)
{
	PyObject* obj;
	globalobjectdef_t* def;
	cpyobjheaddef_t* cpydef;

	/* Patch all locations that need to contain a specific PyObject*.
	   This must go after the previous loop, otherwise
	   PyDict_GetItemString() might not find some of them.
	 */
	for (def = globtable; def->p != NULL; def++) {
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
	/* All objects should be valid at this point.  Loop again and
	   make sure all types are ready, and call the user-defined setups.
	*/
	for (cpydef = cpyheadtable; cpydef->name != NULL; cpydef++) {
		obj = cpydef->cpyobj;
		if (PyType_Check(obj)) {
			if (PyType_Ready((PyTypeObject*) obj) < 0)
				return -1;
		}
		if (cpydef->setupfn) {
			cpydef->setupfn(obj);
			if (RPyExceptionOccurred()) {
				RPyConvertExceptionToCPython();
				return -1;
			}
		}
	}
	return 0;
}

static int setup_globalfunctions(globalfunctiondef_t* def, char* modname)
{
	PyObject* fn;
	PyObject* modname_o = PyString_FromString(modname);
	if (modname_o == NULL)
		return -1;

	for (; def->p != NULL; def++) {
		fn = PyCFunction_NewEx(&def->ml, NULL, modname_o);
		if (fn == NULL)
			return -1;
		fn->ob_type = &PyGenCFunction_Type;
		*def->p = fn;   /* store the object ref in the global var */

		if (PyDict_SetItemString(this_module_globals,
					 def->gfunc_name,
					 fn) < 0)
			return -1;
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

static PyObject *postsetup_get_typedict(PyObject *tp)
{
    PyTypeObject *type = (PyTypeObject *)tp;
    PyObject *ret;

    ret = type->tp_dict;
    Py_INCREF(ret);
    return ret;
}

static PyObject *postsetup_get_methodname(int funcidx)
{   
    globalfunctiondef_t *gfuncdef = &globalfunctiondefsptr[funcidx];

    if (gfuncdef->p)
	return PyString_FromString(gfuncdef->gfunc_name);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *postsetup_build_method(int funcidx, PyObject *type)
{   
    globalfunctiondef_t *gfuncdef = &globalfunctiondefsptr[funcidx];

    if (gfuncdef->p)
	return PyDescr_NewMethod((PyTypeObject *)type, &gfuncdef->ml);
    Py_INCREF(Py_None);
    return Py_None;
}

int call_postsetup(PyObject *m)
{
    PyObject *init, *ret;
    
    init = PyDict_GetItemString(this_module_globals, "__init__");
    if (init == NULL) {
	PyErr_Clear();
	return 0;
    }
    ret = PyObject_CallFunction(init, "O", m);
    if (ret == NULL)
	return -1;
    return 0;
}

#endif /* PYPY_NOT_MAIN_FILE */
