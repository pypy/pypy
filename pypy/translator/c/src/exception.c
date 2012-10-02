#include "common_header.h"
#include "structdef.h"
#include "forwarddecl.h"
#include "preimpl.h"
#include "src/exception.h"

#if defined(PYPY_CPYTHON_EXTENSION)
   PyObject *RPythonError;
#endif 

/******************************************************************/
#ifdef HAVE_RTYPER               /* RPython version of exceptions */
/******************************************************************/

void RPyDebugReturnShowException(const char *msg, const char *filename,
                                 long lineno, const char *functionname)
{
#ifdef DO_LOG_EXC
  fprintf(stderr, "%s %s: %s:%ld %s\n", msg,
          RPyFetchExceptionType()->ov_name->items,
          filename, lineno, functionname);
#endif
}

/* Hint: functions and macros not defined here, like RPyRaiseException,
   come from exctransformer via the table in extfunc.py. */

#define RPyFetchException(etypevar, evaluevar, type_of_evaluevar) do {  \
		etypevar = RPyFetchExceptionType();			\
		evaluevar = (type_of_evaluevar)RPyFetchExceptionValue(); \
		RPyClearException();					\
	} while (0)

/* implementations */

void _RPyRaiseSimpleException(RPYTHON_EXCEPTION rexc)
{
	/* XXX msg is ignored */
	RPyRaiseException(RPYTHON_TYPE_OF_EXC_INST(rexc), rexc);
}

#ifdef PYPY_CPYTHON_EXTENSION
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
	v = NULL;
	if (strcmp(clsname, "AssertionError") == 0) {
		/* workaround against the py lib's BuiltinAssertionError */
		pycls = PyExc_AssertionError;
	}
	else if (strcmp(clsname, "StackOverflow") == 0) {
		pycls = PyExc_RuntimeError;
	}
	else {
		pycls = PyDict_GetItemString(PyEval_GetBuiltins(), clsname);
		if (pycls == NULL || !PyExceptionClass_Check(pycls) ||
		    !PyObject_IsSubclass(pycls, PyExc_Exception)) {
			pycls = PyExc_Exception; /* XXX RPythonError */
			v = PyString_FromString(clsname);
		}
	}
	Py_INCREF(pycls);
	tb = NULL;
	RPyClearException();

	PyErr_NormalizeException(&pycls, &v, &tb);
	PyErr_Restore(pycls, v, tb);
}
#endif   /* !PYPY_STANDALONE */

/******************************************************************/
#endif                                             /* HAVE_RTYPER */
/******************************************************************/
