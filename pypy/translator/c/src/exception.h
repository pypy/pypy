
/************************************************************/
/***  C header subsection: exceptions                     ***/

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
#endif
/* !DO_LOG_EXC: define the function anyway, so that we can shut
   off the prints of a debug_exc by remaking only testing_1.o */
void RPyDebugReturnShowException(const char *msg, const char *filename,
                                 long lineno, const char *functionname);

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
