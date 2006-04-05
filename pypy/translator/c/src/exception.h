
/************************************************************/
 /***  C header subsection: exceptions                     ***/

#if !defined(PYPY_STANDALONE) && !defined(PYPY_NOT_MAIN_FILE)
   PyObject *RPythonError;
#endif 

/******************************************************************/
#ifdef HAVE_RTYPER               /* RPython version of exceptions */
/******************************************************************/

#define RPyFetchException(etypevar, evaluevar, type_of_evaluevar) do {  \
		etypevar = RPyFetchExceptionType();			\
		evaluevar = (type_of_evaluevar)RPyFetchExceptionValue(); \
		RPyClearException();					\
	} while (0)

/* prototypes */

#define RPyRaiseSimpleException(exc, msg)   _RPyRaiseSimpleException(R##exc)
void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc);

#ifndef PYPY_STANDALONE
void RPyConvertExceptionFromCPython(void);
void RPyConvertExceptionToCPython(void);
#endif

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc)
{
	/* XXX msg is ignored */
	RPyRaiseException(RPYTHON_TYPE_OF_EXC_INST(rexc), rexc);
}

#ifndef PYPY_STANDALONE
void RPyConvertExceptionFromCPython(void)
{
	/* convert the CPython exception to an RPython one */
	PyObject *exc_type, *exc_value, *exc_tb;
	RPYTHON_EXCEPTION rexc;

	assert(PyErr_Occurred());
	assert(!RPyExceptionOccurred());
	PyErr_Fetch(&exc_type, &exc_value, &exc_tb);

	/* XXX losing the error message here */	
	rexc = RPYTHON_PYEXCCLASS2EXC(exc_type);
	RPyRaiseException(RPYTHON_TYPE_OF_EXC_INST(rexc), rexc);
}

void RPyConvertExceptionToCPython(void)
{
	/* XXX 1. uses officially bad fishing */
	/* XXX 2. looks for exception classes by name, fragile */
	char* clsname;
	PyObject* pycls;
	assert(RPyExceptionOccurred());
	assert(!PyErr_Occurred());
	clsname = RPyFetchExceptionType()->ov_name->items;
	pycls = PyDict_GetItemString(PyEval_GetBuiltins(), clsname);
	if (pycls != NULL && PyClass_Check(pycls) &&
	    PyClass_IsSubclass(pycls, PyExc_Exception)) {
		PyErr_SetNone(pycls);
	}
	else {
		PyErr_SetString(RPythonError, clsname);
	}
	RPyClearException();
}
#endif   /* !PYPY_STANDALONE */

#endif /* PYPY_NOT_MAIN_FILE */



/******************************************************************/
#else    /* non-RPython version of exceptions, using CPython only */
/******************************************************************/

#define RPyExceptionOccurred()           PyErr_Occurred()
#define RPyRaiseException(etype, evalue) PyErr_Restore(etype, evalue, NULL)
#define RPyFetchException(etypevar, evaluevar, ignored)  do {	\
		PyObject *__tb;					\
		PyErr_Fetch(&etypevar, &evaluevar, &__tb);	\
		if (evaluevar == NULL) {			\
			evaluevar = Py_None;			\
			Py_INCREF(Py_None);			\
		}						\
		Py_XDECREF(__tb);				\
	} while (0)
#define RPyConvertExceptionFromCPython() /* nothing */
#define RPyConvertExceptionToCPython(vanishing) vanishing = NULL  

#define RPyRaiseSimpleException(exc, msg) \
		PyErr_SetString(exc, msg)

/******************************************************************/
#endif                                             /* HAVE_RTYPER */
/******************************************************************/
