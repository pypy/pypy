
/************************************************************/
 /***  C header subsection: exceptions                     ***/

#if !defined(PYPY_STANDALONE) && !defined(PYPY_NOT_MAIN_FILE)
   PyObject *RPythonError;
#endif 

/* just a renaming, unless DO_LOG_EXC is set */
#define RPyExceptionOccurred RPyExceptionOccurred1
#define RPY_DEBUG_RETURN()   /* nothing */

#ifndef PyExceptionClass_Check    /* Python < 2.5 */
# define PyExceptionClass_Check(x)	PyClass_Check(x)
# define PyExceptionInstance_Check(x)	PyInstance_Check(x)
# define PyExceptionInstance_Class(x)	\
				(PyObject*)((PyInstanceObject*)(x))->in_class
#endif


/******************************************************************/
#ifdef HAVE_RTYPER               /* RPython version of exceptions */
/******************************************************************/

#ifdef DO_LOG_EXC
#undef RPyExceptionOccurred
#undef RPY_DEBUG_RETURN
#define RPyExceptionOccurred()  RPyDebugException("  noticing a")
#define RPY_DEBUG_RETURN()      RPyDebugException("leaving with")
#define RPyDebugException(msg)  (                                       \
  RPyExceptionOccurred1()                                               \
    ? (RPyDebugReturnShowException(msg, __FILE__, __LINE__, __FUNCTION__), 1) \
    : 0                                                                 \
  )
void RPyDebugReturnShowException(const char *msg, const char *filename,
                                 long lineno, const char *functionname);
#ifndef PYPY_NOT_MAIN_FILE
void RPyDebugReturnShowException(const char *msg, const char *filename,
                                 long lineno, const char *functionname)
{
  fprintf(stderr, "%s %s: %s:%ld %s\n", msg,
          RPyFetchExceptionType()->ov_name->items,
          filename, lineno, functionname);
}
#endif
#endif  /* DO_LOG_EXC */

/* Hint: functions and macros not defined here, like RPyRaiseException,
   come from exctransformer via the table in extfunc.py. */

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
	PyObject *pycls, *v, *tb;
	assert(RPyExceptionOccurred());
	assert(!PyErr_Occurred());
	clsname = RPyFetchExceptionType()->ov_name->items;
	pycls = PyDict_GetItemString(PyEval_GetBuiltins(), clsname);
	if (pycls != NULL && PyExceptionClass_Check(pycls) &&
	    PyObject_IsSubclass(pycls, PyExc_Exception)) {
		v = NULL;
	}
	else {
		pycls = PyExc_Exception; /* XXX RPythonError */
		v = PyString_FromString(clsname);
	}
	Py_INCREF(pycls);
	tb = NULL;
	RPyClearException();

	PyErr_NormalizeException(&pycls, &v, &tb);
	PyErr_Restore(pycls, v, tb);
}
#endif   /* !PYPY_STANDALONE */

#endif /* PYPY_NOT_MAIN_FILE */



/******************************************************************/
#else    /* non-RPython version of exceptions, using CPython only */
/******************************************************************/

#define RPyExceptionOccurred1()          PyErr_Occurred()
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
