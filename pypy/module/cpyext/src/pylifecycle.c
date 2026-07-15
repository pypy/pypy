#include "Python.h"

PyThreadState *
Py_NewInterpreter(void)
{
    PyErr_SetString(PyExc_NotImplementedError,
                    "subinterpreters are not supported by PyPy");
    return NULL;
}

void
Py_EndInterpreter(PyThreadState *tstate)
{
    /* no-op: PyPy has no subinterpreters */
}

void
_Py_RestoreSignals(void)
{
#ifdef SIGPIPE
    PyOS_setsig(SIGPIPE, SIG_DFL);
#endif
#ifdef SIGXFZ
    PyOS_setsig(SIGXFZ, SIG_DFL);
#endif
#ifdef SIGXFSZ
    PyOS_setsig(SIGXFSZ, SIG_DFL);
#endif
}
