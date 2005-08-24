
/************************************************************/
 /***  C header subsection: exceptions                     ***/

#ifndef PYPY_STANDALONE
   static PyObject *RPythonError;
#endif 

/******************************************************************/
#ifdef HAVE_RTYPER               /* RPython version of exceptions */
/******************************************************************/

static RPYTHON_EXCEPTION_VTABLE	rpython_exc_type = NULL;
static RPYTHON_EXCEPTION	rpython_exc_value = NULL;

#define RPyExceptionOccurred()	(rpython_exc_type != NULL)

#define RPyRaiseException(etype, evalue)		\
		assert(!RPyExceptionOccurred());	\
		rpython_exc_type = etype;	\
		rpython_exc_value = evalue

#define RPyFetchException(etypevar, evaluevar, type_of_evaluevar)       \
		etypevar = rpython_exc_type;				\
		evaluevar = (type_of_evaluevar) rpython_exc_value;	\
		rpython_exc_type = NULL;				\
		rpython_exc_value = NULL

#define RPyMatchException(etype)	RPYTHON_EXCEPTION_MATCH(rpython_exc_type,  \
					(RPYTHON_EXCEPTION_VTABLE) etype)

#ifndef PYPY_STANDALONE
static void RPyConvertExceptionFromCPython(void)
{
	/* convert the CPython exception to an RPython one */
	PyObject *exc_type, *exc_value, *exc_tb;
	assert(PyErr_Occurred());
	assert(!RPyExceptionOccurred());
	PyErr_Fetch(&exc_type, &exc_value, &exc_tb);
	/* XXX loosing the error message here */
	rpython_exc_value = RPYTHON_PYEXCCLASS2EXC(exc_type);
	rpython_exc_type = RPYTHON_TYPE_OF_EXC_INST(rpython_exc_value);
}

static void _RPyConvertExceptionToCPython(void)
{
	/* XXX 1. uses officially bad fishing */
	/* XXX 2. looks for exception classes by name, fragile */
	char* clsname;
	PyObject* pycls;
	assert(RPyExceptionOccurred());
	assert(!PyErr_Occurred());
	clsname = rpython_exc_type->ov_name->items;
	pycls = PyDict_GetItemString(PyEval_GetBuiltins(), clsname);
	if (pycls != NULL && PyClass_Check(pycls) &&
	    PyClass_IsSubclass(pycls, PyExc_Exception)) {
		PyErr_SetNone(pycls);
	}
	else {
		PyErr_SetString(RPythonError, clsname);
	}
}

#define RPyConvertExceptionToCPython(vanishing)    \
	_RPyConvertExceptionToCPython();		\
	vanishing = rpython_exc_value;		\
	rpython_exc_type = NULL;		\
	rpython_exc_value = NULL

#endif   /* !PYPY_STANDALONE */


#define RPyRaiseSimpleException(exc, msg)		        \
	/* XXX 1. uses officially bad fishing */		\
	/* XXX 2. msg is ignored */				\
	rpython_exc_type = (R##exc)->o_typeptr;			\
	rpython_exc_value = (R##exc);				\
	PUSH_ALIVE(rpython_exc_value)

/******************************************************************/
#else    /* non-RPython version of exceptions, using CPython only */
/******************************************************************/

#define RPyExceptionOccurred()           PyErr_Occurred()
#define RPyRaiseException(etype, evalue) PyErr_Restore(etype, evalue, NULL)
#define RPyFetchException(etypevar, evaluevar, ignored)   {	\
		PyObject *__tb;					\
		PyErr_Fetch(&etypevar, &evaluevar, &__tb);	\
		if (evaluevar == NULL) {			\
			evaluevar = Py_None;			\
			Py_INCREF(Py_None);			\
		}						\
		Py_XDECREF(__tb);				\
	}
#define RPyMatchException(etype)         PyErr_ExceptionMatches(etype)
#define RPyConvertExceptionFromCPython() /* nothing */
#define RPyConvertExceptionToCPython(vanishing) vanishing = NULL  

#define RPyRaiseSimpleException(exc, msg) \
		PyErr_SetString(exc, msg)

/******************************************************************/
#endif                                             /* HAVE_RTYPER */
/******************************************************************/
