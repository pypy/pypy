
/************************************************************/
 /***  C header subsection: exceptions                     ***/

#if !defined(PYPY_STANDALONE) && !defined(PYPY_NOT_MAIN_FILE)
   PyObject *RPythonError;
#endif 

/******************************************************************/
#ifdef HAVE_RTYPER               /* RPython version of exceptions */
/******************************************************************/

#ifdef PYPY_NOT_MAIN_FILE
extern RPYTHON_EXCEPTION_VTABLE	rpython_exc_type;
extern RPYTHON_EXCEPTION	rpython_exc_value;
#else
RPYTHON_EXCEPTION_VTABLE	rpython_exc_type = NULL;
RPYTHON_EXCEPTION		rpython_exc_value = NULL;
#endif

#define RPyExceptionOccurred()	(rpython_exc_type != NULL)

#define RPyRaiseException(etype, evalue)	do {	\
		assert(!RPyExceptionOccurred());	\
		rpython_exc_type = etype;		\
		rpython_exc_value = evalue;		\
	} while (0)

#define RPyFetchException(etypevar, evaluevar, type_of_evaluevar) do {  \
		etypevar = rpython_exc_type;				\
		evaluevar = (type_of_evaluevar) rpython_exc_value;	\
		rpython_exc_type = NULL;				\
		rpython_exc_value = NULL;				\
	} while (0)

#define RPyMatchException(etype)	RPYTHON_EXCEPTION_MATCH(rpython_exc_type,  \
					(RPYTHON_EXCEPTION_VTABLE) etype)


/* prototypes */

#define RPyRaiseSimpleException(exc, msg)   _RPyRaiseSimpleException(R##exc)
void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc);

#ifndef PYPY_STANDALONE
void RPyConvertExceptionFromCPython(void);
void _RPyConvertExceptionToCPython(void);
#define RPyConvertExceptionToCPython(vanishing)    \
	_RPyConvertExceptionToCPython();		\
	vanishing = rpython_exc_value;		\
	rpython_exc_type = NULL;		\
	rpython_exc_value = NULL
#endif


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc)
{
	/* XXX 1. uses officially bad fishing */
	/* XXX 2. msg is ignored */
	rpython_exc_type = rexc->o_typeptr;
	rpython_exc_value = rexc;
	PUSH_ALIVE(rpython_exc_value);
}

#ifndef PYPY_STANDALONE
void RPyConvertExceptionFromCPython(void)
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

void _RPyConvertExceptionToCPython(void)
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
#define RPyMatchException(etype)         PyErr_ExceptionMatches(etype)
#define RPyConvertExceptionFromCPython() /* nothing */
#define RPyConvertExceptionToCPython(vanishing) vanishing = NULL  

#define RPyRaiseSimpleException(exc, msg) \
		PyErr_SetString(exc, msg)

/******************************************************************/
#endif                                             /* HAVE_RTYPER */
/******************************************************************/
