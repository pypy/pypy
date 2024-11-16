/* Interface to random parts in ceval.c */

#ifndef Py_CEVAL_H
#define Py_CEVAL_H
#ifdef __cplusplus
extern "C" {
#endif


/* PyEval_CallObjectWithKeywords(), PyEval_CallObject(), PyEval_CallFunction
 * and PyEval_CallMethod are deprecated. Since they are officially part of the
 * stable ABI (PEP 384), they must be kept for backward compatibility.
 * PyObject_Call(), PyObject_CallFunction() and PyObject_CallMethod() are
 * recommended to call a callable object.
 */

#ifndef PYPY_VERSION
Py_DEPRECATED(3.9) PyAPI_FUNC(PyObject *) PyEval_CallObjectWithKeywords(
    PyObject *callable,
    PyObject *args,
    PyObject *kwargs);
#endif

/* Deprecated since PyEval_CallObjectWithKeywords is deprecated */
#define PyEval_CallObject(callable, arg) \
    PyEval_CallObjectWithKeywords(callable, arg, (PyObject *)NULL)

Py_DEPRECATED(3.9) PyAPI_FUNC(PyObject *) PyEval_CallFunction(
    PyObject *callable, const char *format, ...);
Py_DEPRECATED(3.9) PyAPI_FUNC(PyObject *) PyEval_CallMethod(
    PyObject *obj, const char *name, const char *format, ...);



/* Interface for threads.

   A module that plans to do a blocking system call (or something else
   that lasts a long time and doesn't touch Python data) can allow other
   threads to run as follows:

    ...preparations here...
    Py_BEGIN_ALLOW_THREADS
    ...blocking system call here...
    Py_END_ALLOW_THREADS
    ...interpret result here...

   The Py_BEGIN_ALLOW_THREADS/Py_END_ALLOW_THREADS pair expands to a
   {}-surrounded block.
   To leave the block in the middle (e.g., with return), you must insert
   a line containing Py_BLOCK_THREADS before the return, e.g.

    if (...premature_exit...) {
        Py_BLOCK_THREADS
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

   An alternative is:

    Py_BLOCK_THREADS
    if (...premature_exit...) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    Py_UNBLOCK_THREADS

   For convenience, that the value of 'errno' is restored across
   Py_END_ALLOW_THREADS and Py_BLOCK_THREADS.

   WARNING: NEVER NEST CALLS TO Py_BEGIN_ALLOW_THREADS AND
   Py_END_ALLOW_THREADS!!!

   Note that not yet all candidates have been converted to use this
   mechanism!
*/


#define Py_BEGIN_ALLOW_THREADS { \
                        PyThreadState *_save; \
                        _save = PyEval_SaveThread();
#define Py_BLOCK_THREADS        PyEval_RestoreThread(_save);
#define Py_UNBLOCK_THREADS      _save = PyEval_SaveThread();
#define Py_END_ALLOW_THREADS    PyEval_RestoreThread(_save); \
                 }


#ifndef PYPY_VERSION
PyAPI_FUNC(const char *) PyEval_GetFuncName(PyObject *);
#endif
PyAPI_FUNC(const char *) PyEval_GetFuncDesc(PyObject *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_CEVAL_H */
